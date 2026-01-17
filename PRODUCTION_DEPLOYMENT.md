# Production Deployment Guide

This guide covers deploying the CMS application in a production environment with high availability, monitoring, and security best practices.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Domain name with SSL certificate
- PostgreSQL 15+ (or use containerized version)
- Redis 7+ (or use containerized version)

## Architecture Overview

```
                    ┌─────────────┐
                    │   Nginx     │
                    │   (LB)      │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────┴─────┐ ┌────┴────┐ ┌─────┴─────┐
        │   Web 1   │ │  Web 2  │ │   Web N   │
        │  (FastAPI)│ │(FastAPI)│ │ (FastAPI) │
        └─────┬─────┘ └────┬────┘ └─────┬─────┘
              │            │            │
              └────────────┼────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────┴────┐      ┌─────┴─────┐     ┌────┴────┐
    │PostgreSQL│     │   Redis   │     │  Loki   │
    │ Primary  │     │  Cluster  │     │  Logs   │
    └──────────┘     └───────────┘     └─────────┘
```

## Quick Start

### 1. Clone and Configure

```bash
git clone https://github.com/your-org/cms-project.git
cd cms-project

# Copy environment template
cp .env.example .env.prod
```

### 2. Configure Environment Variables

Edit `.env.prod` with production values:

```bash
# Application
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<generate-strong-secret>

# Database
DATABASE_URL=postgresql+asyncpg://user:password@db:5432/cms_prod
DATABASE_USER=cms_user
DATABASE_PASSWORD=<strong-password>
DATABASE_NAME=cms_prod

# Redis
REDIS_URL=redis://default:<password>@redis:6379/0
REDIS_PASSWORD=<strong-password>

# Security
ALLOWED_ORIGINS=https://your-domain.com
```

### 3. Deploy with Docker Compose

```bash
# Build and start services
docker-compose -f docker-compose.prod.yml up -d

# With monitoring stack
docker-compose -f docker-compose.prod.yml --profile monitoring up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### 4. Run Database Migrations

```bash
docker-compose -f docker-compose.prod.yml exec web1 alembic upgrade head
```

## Configuration Files

### Nginx Configuration (`nginx/nginx.conf`)

The Nginx configuration provides:
- Load balancing with least connections algorithm
- Rate limiting (10 requests/second with burst of 20)
- Health check passthrough
- Gzip compression
- Security headers
- Request ID propagation

### Prometheus Configuration (`prometheus/prometheus.yml`)

Prometheus scrapes metrics from:
- Application instances (`/metrics` endpoint)
- Self-monitoring

## Health Checks

### Liveness Probe (`/health`)
- Returns 200 if application is running
- Used by orchestrators to determine if container should be restarted
- Does not check external dependencies

```bash
curl http://localhost:8000/health
```

### Readiness Probe (`/ready`)
- Returns 200 if application can handle requests
- Checks database and Redis connectivity
- Used by load balancers to determine if traffic should be routed

```bash
curl http://localhost:8000/ready
```

### Detailed Health (`/health/detailed`)
- Returns comprehensive health information
- Includes all dependency statuses with latency

```bash
curl http://localhost:8000/health/detailed
```

## Monitoring

### Prometheus Metrics (`/metrics`)

Available metrics:
- `cms_uptime_seconds` - Application uptime
- `cms_http_requests_total` - Total HTTP requests
- `cms_db_queries_total` - Database query count
- `cms_cache_hits_total` / `cms_cache_misses_total` - Cache efficiency

### Grafana Dashboards

Access Grafana at `http://localhost:3000` (default credentials: admin/admin)

### Log Aggregation

Logs are output in JSON format for easy parsing:

```json
{
  "timestamp": "2024-01-17T12:00:00Z",
  "level": "INFO",
  "logger": "cms.access",
  "message": "GET /api/v1/content - 200 (45.23ms)",
  "request_id": "abc-123",
  "method": "GET",
  "path": "/api/v1/content",
  "status_code": 200,
  "duration_ms": 45.23,
  "client_ip": "192.168.1.1"
}
```

## Scaling

### Horizontal Scaling

Add more application instances:

```bash
# Scale to 4 instances
docker-compose -f docker-compose.prod.yml up -d --scale web=4
```

Update `nginx/nginx.conf` to include new backends or use Docker service discovery.

### Database Scaling

For read-heavy workloads, add read replicas:

1. Configure PostgreSQL streaming replication
2. Update application to use read replicas for queries
3. Use PgBouncer for connection pooling

### Redis Scaling

For high-availability Redis:

1. Deploy Redis Sentinel or Redis Cluster
2. Update `REDIS_URL` to use Sentinel endpoints

## Security Checklist

- [ ] Use strong, unique passwords for all services
- [ ] Enable SSL/TLS for all external connections
- [ ] Configure firewall rules to restrict access
- [ ] Enable database connection encryption
- [ ] Set up regular automated backups
- [ ] Configure log retention policies
- [ ] Enable rate limiting at Nginx level
- [ ] Review and update dependencies regularly
- [ ] Set up intrusion detection monitoring
- [ ] Configure CORS for specific origins only

## Backup and Recovery

### Database Backups

```bash
# Manual backup
docker-compose -f docker-compose.prod.yml exec db pg_dump -U cms_user cms_prod > backup.sql

# Restore
docker-compose -f docker-compose.prod.yml exec -T db psql -U cms_user cms_prod < backup.sql
```

### Automated Backups

Add a backup service to docker-compose:

```yaml
backup:
  image: prodrigestivill/postgres-backup-local
  environment:
    - POSTGRES_HOST=db
    - POSTGRES_DB=cms_prod
    - POSTGRES_USER=cms_user
    - POSTGRES_PASSWORD=${DATABASE_PASSWORD}
    - SCHEDULE=@daily
    - BACKUP_KEEP_DAYS=7
  volumes:
    - ./backups:/backups
```

## Troubleshooting

### Application Not Starting

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs web1

# Check health
curl http://localhost:8000/health/detailed
```

### Database Connection Issues

```bash
# Test connection
docker-compose -f docker-compose.prod.yml exec web1 python -c "
from app.database import engine
import asyncio
async def test():
    async with engine.connect() as conn:
        print('Connected!')
asyncio.run(test())
"
```

### Redis Connection Issues

```bash
# Test Redis
docker-compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD ping
```

### Performance Issues

1. Check Prometheus metrics for bottlenecks
2. Review slow query logs in PostgreSQL
3. Monitor cache hit rates
4. Check Nginx access logs for high latency requests

## CI/CD Integration

The GitHub Actions workflow (`.github/workflows/ci-cd.yml`) provides:

1. **Quality Checks**: Linting, security scanning
2. **Testing**: Unit and integration tests
3. **Build**: Docker image creation and push to GHCR
4. **Security Scan**: Trivy vulnerability scanning
5. **Deploy**: Automated deployment to staging/production

### Deployment Triggers

- Push to `develop` → Deploy to staging
- Tag `v*` → Deploy to production

### Required Secrets

Configure in GitHub repository settings:
- `CODECOV_TOKEN` - Coverage reporting
- `STAGING_*` - Staging environment credentials
- `PRODUCTION_*` - Production environment credentials

## GDPR Compliance

The application includes GDPR compliance features:

- **Data Export** (`/api/v1/privacy/export`) - Users can export all their data
- **Account Deletion** (`/api/v1/privacy/delete-account`) - Complete data erasure
- **Consent Management** (`/api/v1/privacy/settings`) - Manage consent preferences
- **Data Summary** (`/api/v1/privacy/data-summary`) - View data overview

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/cms-project/issues
- Documentation: See project README and docs folder
