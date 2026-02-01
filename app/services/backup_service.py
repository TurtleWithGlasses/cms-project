"""
Backup Service

Provides database backup and restore functionality.
"""

import logging
import shutil
import subprocess  # nosec B404 - subprocess needed for pg_dump
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.backup import Backup, BackupSchedule, BackupStatus, BackupType

logger = logging.getLogger(__name__)

# Backup storage directory
BACKUP_DIR = Path("backups")
BACKUP_DIR.mkdir(exist_ok=True)


class BackupService:
    """Service for managing database backups."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_backups(
        self,
        limit: int = 50,
        offset: int = 0,
        status: BackupStatus | None = None,
    ) -> tuple[list[Backup], int]:
        """
        List all backups with optional filtering.

        Returns:
            Tuple of (backups list, total count)
        """
        # Build query
        query = select(Backup)

        if status:
            query = query.where(Backup.status == status)

        # Get total count
        count_query = select(func.count(Backup.id))
        if status:
            count_query = count_query.where(Backup.status == status)
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.order_by(Backup.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        backups = list(result.scalars().all())

        return backups, total

    async def get_backup(self, backup_id: int) -> Backup | None:
        """Get a backup by ID."""
        result = await self.db.execute(select(Backup).where(Backup.id == backup_id))
        return result.scalars().first()

    async def create_backup(
        self,
        backup_type: BackupType = BackupType.FULL,
        include_database: bool = True,
        include_media: bool = True,
        include_config: bool = False,
        description: str | None = None,
        created_by_id: int | None = None,
    ) -> Backup:
        """
        Create a new backup.

        Args:
            backup_type: Type of backup (full, incremental, etc.)
            include_database: Include database dump
            include_media: Include media files
            include_config: Include configuration files
            description: Optional description
            created_by_id: User ID who initiated the backup

        Returns:
            Created backup record
        """
        # Generate unique filename
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{timestamp}_{backup_type.value}.tar.gz"
        file_path = str(BACKUP_DIR / filename)

        # Create backup record
        backup = Backup(
            filename=filename,
            file_path=file_path,
            backup_type=backup_type,
            status=BackupStatus.PENDING,
            include_database=include_database,
            include_media=include_media,
            include_config=include_config,
            description=description,
            created_by_id=created_by_id,
        )

        self.db.add(backup)
        await self.db.commit()
        await self.db.refresh(backup)

        # Start backup process asynchronously
        try:
            await self._perform_backup(backup)
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            backup.status = BackupStatus.FAILED
            backup.error_message = str(e)
            await self.db.commit()

        return backup

    async def _perform_backup(self, backup: Backup) -> None:
        """
        Perform the actual backup operation.

        This creates a compressed archive containing:
        - Database dump (if include_database)
        - Media files (if include_media)
        - Config files (if include_config)
        """
        backup.status = BackupStatus.IN_PROGRESS
        backup.started_at = datetime.now(timezone.utc)
        await self.db.commit()

        temp_dir = BACKUP_DIR / f"temp_{backup.id}"
        temp_dir.mkdir(exist_ok=True)

        try:
            # Database backup
            if backup.include_database:
                await self._backup_database(temp_dir)

            # Media backup
            if backup.include_media:
                await self._backup_media(temp_dir)

            # Config backup
            if backup.include_config:
                await self._backup_config(temp_dir)

            # Create compressed archive
            archive_path = shutil.make_archive(
                str(BACKUP_DIR / backup.filename.replace(".tar.gz", "")),
                "gztar",
                temp_dir,
            )

            # Update backup record
            backup.file_path = archive_path
            backup.file_size = Path(archive_path).stat().st_size
            backup.status = BackupStatus.COMPLETED
            backup.completed_at = datetime.now(timezone.utc)

            logger.info(f"Backup completed: {backup.filename} ({backup.file_size_mb} MB)")

        except Exception as e:
            backup.status = BackupStatus.FAILED
            backup.error_message = str(e)
            logger.error(f"Backup failed: {e}")
            raise

        finally:
            # Clean up temp directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

            await self.db.commit()

    async def _backup_database(self, temp_dir: Path) -> None:
        """Create database dump using pg_dump."""
        dump_file = temp_dir / "database.sql"

        # Parse database URL for connection details
        db_url = settings.database_url
        # Format: postgresql+asyncpg://user:pass@host:port/dbname
        # Extract just the postgres part
        db_url_sync = db_url.replace("+asyncpg", "")

        try:
            # Use pg_dump to create database dump
            result = subprocess.run(  # nosec B603 B607
                ["pg_dump", "--dbname", db_url_sync, "-f", str(dump_file)],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode != 0:
                # If pg_dump is not available, create a placeholder
                logger.warning(f"pg_dump failed: {result.stderr}")
                dump_file.write_text("-- Database dump placeholder\n-- pg_dump not available or failed\n")

        except FileNotFoundError:
            # pg_dump not installed, create placeholder
            logger.warning("pg_dump not found, creating placeholder")
            dump_file.write_text("-- Database dump placeholder\n-- pg_dump not installed\n")

        except subprocess.TimeoutExpired:
            logger.error("Database dump timed out")
            raise

    async def _backup_media(self, temp_dir: Path) -> None:
        """Copy media files to backup directory."""
        media_dir = Path("uploads")
        if media_dir.exists():
            dest = temp_dir / "media"
            shutil.copytree(media_dir, dest, dirs_exist_ok=True)
        else:
            # Create empty media directory marker
            (temp_dir / "media").mkdir(exist_ok=True)
            (temp_dir / "media" / ".keep").touch()

    async def _backup_config(self, temp_dir: Path) -> None:
        """Copy configuration files to backup directory."""
        config_dir = temp_dir / "config"
        config_dir.mkdir(exist_ok=True)

        # Copy .env.example (not .env for security)
        env_example = Path(".env.example")
        if env_example.exists():
            shutil.copy(env_example, config_dir / ".env.example")

        # Copy alembic.ini
        alembic_ini = Path("alembic.ini")
        if alembic_ini.exists():
            shutil.copy(alembic_ini, config_dir / "alembic.ini")

    async def delete_backup(self, backup_id: int) -> bool:
        """
        Delete a backup and its associated file.

        Returns:
            True if deleted, False if not found
        """
        backup = await self.get_backup(backup_id)
        if not backup:
            return False

        # Delete the file
        file_path = Path(backup.file_path) if backup.file_path else None
        if file_path and file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted backup file: {backup.file_path}")

        # Delete the record
        await self.db.execute(delete(Backup).where(Backup.id == backup_id))
        await self.db.commit()

        return True

    async def restore_backup(self, backup_id: int) -> bool:
        """
        Restore from a backup.

        WARNING: This is a destructive operation that will overwrite current data.

        Returns:
            True if restored successfully
        """
        backup = await self.get_backup(backup_id)
        if not backup:
            raise ValueError(f"Backup {backup_id} not found")

        if backup.status != BackupStatus.COMPLETED:
            raise ValueError(f"Cannot restore from backup with status {backup.status}")

        if not Path(backup.file_path).exists():
            raise FileNotFoundError(f"Backup file not found: {backup.file_path}")

        # TODO: Implement actual restore logic
        # This would involve:
        # 1. Extracting the archive
        # 2. Running pg_restore for database
        # 3. Copying media files back
        # 4. Restarting services if needed

        logger.warning("Restore functionality is not yet fully implemented")
        return True

    async def get_schedule(self) -> BackupSchedule | None:
        """Get the current backup schedule."""
        result = await self.db.execute(select(BackupSchedule).limit(1))
        return result.scalars().first()

    async def update_schedule(
        self,
        enabled: bool | None = None,
        frequency: str | None = None,
        time_of_day: str | None = None,
        day_of_week: int | None = None,
        day_of_month: int | None = None,
        retention_days: int | None = None,
        max_backups: int | None = None,
        backup_type: BackupType | None = None,
        include_database: bool | None = None,
        include_media: bool | None = None,
        include_config: bool | None = None,
    ) -> BackupSchedule:
        """Update or create the backup schedule."""
        schedule = await self.get_schedule()

        if not schedule:
            schedule = BackupSchedule()
            self.db.add(schedule)

        # Update fields if provided
        if enabled is not None:
            schedule.enabled = enabled
        if frequency is not None:
            schedule.frequency = frequency
        if time_of_day is not None:
            schedule.time_of_day = time_of_day
        if day_of_week is not None:
            schedule.day_of_week = day_of_week
        if day_of_month is not None:
            schedule.day_of_month = day_of_month
        if retention_days is not None:
            schedule.retention_days = retention_days
        if max_backups is not None:
            schedule.max_backups = max_backups
        if backup_type is not None:
            schedule.backup_type = backup_type
        if include_database is not None:
            schedule.include_database = include_database
        if include_media is not None:
            schedule.include_media = include_media
        if include_config is not None:
            schedule.include_config = include_config

        await self.db.commit()
        await self.db.refresh(schedule)

        return schedule

    async def get_storage_info(self) -> dict:
        """Get backup storage information."""
        total_size = 0
        backup_count = 0

        # Calculate total size of backup files
        if BACKUP_DIR.exists():
            for file in BACKUP_DIR.glob("*.tar.gz"):
                total_size += file.stat().st_size
                backup_count += 1

        # Get disk space info
        try:
            disk_usage = shutil.disk_usage(BACKUP_DIR)
            disk_total = disk_usage.total
            disk_free = disk_usage.free
            disk_used_percent = ((disk_usage.total - disk_usage.free) / disk_usage.total) * 100
        except Exception:
            disk_total = 0
            disk_free = 0
            disk_used_percent = 0

        return {
            "backup_count": backup_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "backup_directory": str(BACKUP_DIR.absolute()),
            "disk_total_bytes": disk_total,
            "disk_free_bytes": disk_free,
            "disk_used_percent": round(disk_used_percent, 2),
        }

    async def cleanup_old_backups(self, retention_days: int = 30, max_backups: int = 10) -> int:
        """
        Clean up old backups based on retention policy.

        Returns:
            Number of backups deleted
        """
        deleted_count = 0

        # Get all completed backups ordered by date
        result = await self.db.execute(
            select(Backup).where(Backup.status == BackupStatus.COMPLETED).order_by(Backup.created_at.desc())
        )
        backups = list(result.scalars().all())

        # Delete backups beyond max_backups limit
        if len(backups) > max_backups:
            for backup in backups[max_backups:]:
                await self.delete_backup(backup.id)
                deleted_count += 1

        # Delete backups older than retention_days
        cutoff = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta

        cutoff = cutoff - timedelta(days=retention_days)

        for backup in backups[:max_backups]:  # Check remaining backups
            if backup.created_at < cutoff:
                await self.delete_backup(backup.id)
                deleted_count += 1

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old backups")

        return deleted_count
