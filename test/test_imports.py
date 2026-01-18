"""Tests for import functionality."""

import pytest

from app.models.import_job import (
    DuplicateHandling,
    ExportJob,
    ImportFormat,
    ImportJob,
    ImportRecord,
    ImportStatus,
    ImportType,
)


class TestImportModels:
    """Test Import models."""

    def test_import_job_creation(self):
        """Test creating an ImportJob instance."""
        job = ImportJob(
            name="Test Import",
            import_type=ImportType.CONTENT,
            import_format=ImportFormat.JSON,
            file_name="content.json",
        )
        assert job.name == "Test Import"
        assert job.import_type == ImportType.CONTENT
        assert job.import_format == ImportFormat.JSON
        assert job.file_name == "content.json"

    def test_import_job_defaults(self):
        """Test ImportJob default values."""
        job = ImportJob(
            name="Test",
            import_type=ImportType.CONTENT,
            import_format=ImportFormat.CSV,
            file_name="test.csv",
        )
        assert job.status == ImportStatus.PENDING
        assert job.duplicate_handling == DuplicateHandling.SKIP
        assert job.total_records == 0
        assert job.processed_records == 0
        assert job.successful_records == 0
        assert job.failed_records == 0
        assert job.skipped_records == 0

    def test_import_record_creation(self):
        """Test creating an ImportRecord instance."""
        record = ImportRecord(
            import_job_id=1,
            row_number=5,
            source_id="ext-123",
        )
        assert record.import_job_id == 1
        assert record.row_number == 5
        assert record.source_id == "ext-123"
        assert record.status == ImportStatus.PENDING

    def test_export_job_creation(self):
        """Test creating an ExportJob instance."""
        job = ExportJob(
            name="User Export",
            export_type=ImportType.USERS,
            export_format=ImportFormat.CSV,
        )
        assert job.name == "User Export"
        assert job.export_type == ImportType.USERS
        assert job.export_format == ImportFormat.CSV


class TestImportEnums:
    """Test import-related enums."""

    def test_import_type_values(self):
        """Test ImportType enum values."""
        assert ImportType.CONTENT.value == "content"
        assert ImportType.USERS.value == "users"
        assert ImportType.CATEGORIES.value == "categories"
        assert ImportType.TAGS.value == "tags"
        assert ImportType.MEDIA.value == "media"
        assert ImportType.MIXED.value == "mixed"

    def test_import_format_values(self):
        """Test ImportFormat enum values."""
        assert ImportFormat.JSON.value == "json"
        assert ImportFormat.CSV.value == "csv"
        assert ImportFormat.XML.value == "xml"

    def test_import_status_values(self):
        """Test ImportStatus enum values."""
        assert ImportStatus.PENDING.value == "pending"
        assert ImportStatus.VALIDATING.value == "validating"
        assert ImportStatus.PROCESSING.value == "processing"
        assert ImportStatus.COMPLETED.value == "completed"
        assert ImportStatus.FAILED.value == "failed"
        assert ImportStatus.CANCELLED.value == "cancelled"
        assert ImportStatus.PARTIAL.value == "partial"

    def test_duplicate_handling_values(self):
        """Test DuplicateHandling enum values."""
        assert DuplicateHandling.SKIP.value == "skip"
        assert DuplicateHandling.UPDATE.value == "update"
        assert DuplicateHandling.CREATE_NEW.value == "create_new"
        assert DuplicateHandling.FAIL.value == "fail"


class TestImportService:
    """Test import service functions."""

    @pytest.mark.asyncio
    async def test_parse_json_content(self):
        """Test JSON parsing."""
        from app.services.import_service import parse_json_content

        # Test list format
        json_list = b'[{"title": "Test 1"}, {"title": "Test 2"}]'
        result = await parse_json_content(json_list)
        assert len(result) == 2
        assert result[0]["title"] == "Test 1"

        # Test object with items key
        json_items = b'{"items": [{"title": "Item 1"}]}'
        result = await parse_json_content(json_items)
        assert len(result) == 1
        assert result[0]["title"] == "Item 1"

        # Test single object
        json_single = b'{"title": "Single"}'
        result = await parse_json_content(json_single)
        assert len(result) == 1
        assert result[0]["title"] == "Single"

    @pytest.mark.asyncio
    async def test_parse_csv_content(self):
        """Test CSV parsing."""
        from app.services.import_service import parse_csv_content

        csv_content = b"title,body\nTest Title,Test Body\nAnother,Content"
        result = await parse_csv_content(csv_content)
        assert len(result) == 2
        assert result[0]["title"] == "Test Title"
        assert result[0]["body"] == "Test Body"

    @pytest.mark.asyncio
    async def test_apply_field_mapping(self):
        """Test field mapping application."""
        from app.services.import_service import apply_field_mapping

        data = {"name": "Test", "desc": "Description", "extra": "Value"}
        mapping = {"name": "title", "desc": "body"}

        result = await apply_field_mapping(data, mapping)
        assert result["title"] == "Test"
        assert result["body"] == "Description"
        assert result["extra"] == "Value"  # Unmapped field preserved

    @pytest.mark.asyncio
    async def test_validate_content_record(self):
        """Test content record validation."""
        from app.services.import_service import validate_content_record

        # Valid record
        valid, error = await validate_content_record({"title": "Test"})
        assert valid is True
        assert error is None

        # Missing title
        valid, error = await validate_content_record({"body": "Content"})
        assert valid is False
        assert "title" in error.lower()

        # Empty title
        valid, error = await validate_content_record({"title": ""})
        assert valid is False
