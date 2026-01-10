# Production Deployment Guide

This guide covers deploying the CMS application to production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Deployment Options](#deployment-options)
- [Environment Configuration](#environment-configuration)
- [Cloud Deployments](#cloud-deployments)
- [CI/CD Pipelines](#cicd-pipelines)
- [Security Hardening](#security-hardening)
- [Monitoring & Logging](#monitoring--logging)
- [Backup & Recovery](#backup--recovery)
- [Scaling](#scaling)

## Prerequisites

Before deploying to production, ensure you have:

- ✅ All tests passing (`pytest`)
- ✅ Security audit completed
- ✅ Environment variables configured
- ✅ SSL/TLS certificates obtained
- ✅ Database backup strategy planned
- ✅ Monitoring solution chosen
- ✅ Domain name and DNS configured

## Deployment Options

### Option 1: Docker Container (Recommended)

Deploy using Docker and docker-compose. See [DOCKER_SETUP.md](DOCKER_SETUP.md) for detailed instructions.

**Best for**: Most production scenarios, easy scaling, consistent environments

### Option 2: Cloud Platform Services

Deploy to managed services (AWS ECS, Azure App Service, Google Cloud Run).

**Best for**: Automatic scaling, managed infrastructure, minimal operations overhead

### Option 3: Traditional VPS

Deploy directly to a virtual private server without containers.

**Best for**: Small deployments, cost optimization, full control

## Environment Configuration

### Production Environment Variables

Create a `.env.production` file (never commit this to git):

```bash
# Application
APP_NAME="CMS Production"
APP_VERSION="1.0.0"
ENVIRONMENT=production
DEBUG=False

# Security
SECRET_KEY=<GENERATE_WITH_openssl_rand_-hex_32>
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Database (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://cms_user:STRONG_PASSWORD@db-host:5432/cms_prod
DATABASE_USER=cms_user
DATABASE_PASSWORD=<STRONG_PASSWORD>
DATABASE_NAME=cms_prod
DATABASE_HOST=db-host
DATABASE_PORT=5432

# Redis
REDIS_URL=redis://default:STRONG_REDIS_PASSWORD@redis-host:6379/0
REDIS_PASSWORD=<STRONG_REDIS_PASSWORD>

# JWT Authentication
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Email (for password reset)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=<APP_PASSWORD>
SMTP_FROM=noreply@yourdomain.com

# Rate Limiting
RATE_LIMIT_ENABLED=True
RATE_LIMIT_PER_MINUTE=60

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/cms/app.log

# Monitoring
SENTRY_DSN=<YOUR_SENTRY_DSN>
```

### Generate Secure Keys

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate passwords
openssl rand -base64 24
```

### Environment-Specific Settings

#### Development
```bash
ENVIRONMENT=development
DEBUG=True
DATABASE_URL=sqlite+aiosqlite:///./cms.db
```

#### Staging
```bash
ENVIRONMENT=staging
DEBUG=False
DATABASE_URL=postgresql+asyncpg://cms_user:password@staging-db:5432/cms_staging
```

#### Production
```bash
ENVIRONMENT=production
DEBUG=False
DATABASE_URL=postgresql+asyncpg://cms_user:password@prod-db:5432/cms_prod
```

## Cloud Deployments

### AWS Deployment

#### Option A: AWS ECS (Elastic Container Service)

**Architecture**:
- ECS Fargate for container orchestration
- RDS PostgreSQL for database
- ElastiCache Redis for sessions
- ALB (Application Load Balancer) for traffic
- Route 53 for DNS

**Steps**:

1. **Build and Push Docker Image**:

```bash
# Authenticate to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build image
docker build -t cms-app:latest .

# Tag image
docker tag cms-app:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/cms-app:latest

# Push image
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/cms-app:latest
```

2. **Create ECS Task Definition** (`task-definition.json`):

```json
{
  "family": "cms-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "cms-web",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/cms-app:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "DEBUG", "value": "False"}
      ],
      "secrets": [
        {"name": "SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:us-east-1:account-id:secret:cms/secret-key"},
        {"name": "DATABASE_URL", "valueFrom": "arn:aws:secretsmanager:us-east-1:account-id:secret:cms/database-url"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/cms-app",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

3. **Create ECS Service**:

```bash
aws ecs create-service \
  --cluster cms-cluster \
  --service-name cms-service \
  --task-definition cms-app \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:account-id:targetgroup/cms-tg/xxx,containerName=cms-web,containerPort=8000"
```

#### Option B: AWS Elastic Beanstalk

**Steps**:

1. Install EB CLI:
```bash
pip install awsebcli
```

2. Initialize Elastic Beanstalk:
```bash
eb init -p docker cms-app --region us-east-1
```

3. Create environment:
```bash
eb create cms-production \
  --database.engine postgres \
  --database.username cms_user \
  --envvars SECRET_KEY=xxx,REDIS_URL=xxx
```

4. Deploy:
```bash
eb deploy
```

### Azure Deployment

#### Azure App Service with Container

**Steps**:

1. **Create Resource Group**:
```bash
az group create --name cms-rg --location eastus
```

2. **Create Container Registry**:
```bash
az acr create --resource-group cms-rg --name cmsregistry --sku Basic
az acr login --name cmsregistry
```

3. **Build and Push Image**:
```bash
docker build -t cmsregistry.azurecr.io/cms-app:latest .
docker push cmsregistry.azurecr.io/cms-app:latest
```

4. **Create PostgreSQL Database**:
```bash
az postgres flexible-server create \
  --resource-group cms-rg \
  --name cms-postgres \
  --location eastus \
  --admin-user cmsadmin \
  --admin-password <STRONG_PASSWORD> \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32
```

5. **Create App Service**:
```bash
az appservice plan create \
  --name cms-plan \
  --resource-group cms-rg \
  --is-linux \
  --sku B1

az webapp create \
  --resource-group cms-rg \
  --plan cms-plan \
  --name cms-app \
  --deployment-container-image-name cmsregistry.azurecr.io/cms-app:latest

# Configure environment variables
az webapp config appsettings set \
  --resource-group cms-rg \
  --name cms-app \
  --settings \
    ENVIRONMENT=production \
    DEBUG=False \
    SECRET_KEY=xxx \
    DATABASE_URL=postgresql+asyncpg://cmsadmin:password@cms-postgres.postgres.database.azure.com:5432/cms
```

### Google Cloud Platform (GCP)

#### Cloud Run Deployment

**Steps**:

1. **Enable APIs**:
```bash
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
```

2. **Build and Push Image**:
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/cms-app
```

3. **Create Cloud SQL PostgreSQL**:
```bash
gcloud sql instances create cms-postgres \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

gcloud sql databases create cms_prod --instance=cms-postgres
```

4. **Deploy to Cloud Run**:
```bash
gcloud run deploy cms-app \
  --image gcr.io/PROJECT_ID/cms-app \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances PROJECT_ID:us-central1:cms-postgres \
  --set-env-vars ENVIRONMENT=production,DEBUG=False \
  --set-secrets SECRET_KEY=cms-secret-key:latest,DATABASE_URL=cms-database-url:latest \
  --min-instances 1 \
  --max-instances 10 \
  --cpu 1 \
  --memory 512Mi
```

### DigitalOcean App Platform

**Steps**:

1. Create `app.yaml`:

```yaml
name: cms-app
services:
  - name: web
    image:
      registry_type: DOCKER_HUB
      repository: yourusername/cms-app
      tag: latest
    instance_count: 2
    instance_size_slug: basic-xs
    http_port: 8000
    health_check:
      http_path: /health
    envs:
      - key: ENVIRONMENT
        value: production
      - key: SECRET_KEY
        value: ${cms.SECRET_KEY}
        type: SECRET
      - key: DATABASE_URL
        value: ${db.DATABASE_URL}
        type: SECRET
    routes:
      - path: /

databases:
  - name: db
    engine: PG
    version: "15"
    size: db-s-1vcpu-1gb
```

2. Deploy:
```bash
doctl apps create --spec app.yaml
```

## CI/CD Pipelines

### GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0
        run: |
          pytest --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v2
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-
            type=semver,pattern={{version}}

      - name: Build and push image
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: production

    steps:
      - name: Deploy to production
        run: |
          # Add your deployment command here
          # Examples:
          # - SSH to server and pull new image
          # - Update ECS service
          # - Deploy to Cloud Run
          # - Update Kubernetes deployment
          echo "Deploying to production..."
```

### GitLab CI

Create `.gitlab-ci.yml`:

```yaml
stages:
  - test
  - build
  - deploy

variables:
  DOCKER_DRIVER: overlay2
  IMAGE_TAG: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA

test:
  stage: test
  image: python:3.10
  services:
    - postgres:15
    - redis:7-alpine
  variables:
    POSTGRES_DB: test_db
    POSTGRES_USER: test_user
    POSTGRES_PASSWORD: test_pass
    DATABASE_URL: postgresql+asyncpg://test_user:test_pass@postgres:5432/test_db
    REDIS_URL: redis://redis:6379/0
  script:
    - pip install -r requirements.txt
    - pytest --cov=app --cov-report=term
  coverage: '/TOTAL.*\s+(\d+%)$/'

build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - docker build -t $IMAGE_TAG .
    - docker push $IMAGE_TAG
  only:
    - main

deploy_production:
  stage: deploy
  image: alpine:latest
  before_script:
    - apk add --no-cache curl
  script:
    - echo "Deploying to production..."
    # Add deployment commands here
  environment:
    name: production
    url: https://cms.yourdomain.com
  only:
    - main
  when: manual
```

## Security Hardening

### Application Security

#### 1. Use Strong Secret Keys

```bash
# Generate new SECRET_KEY for production
openssl rand -hex 32
```

Never reuse development secrets in production.

#### 2. Enable HTTPS Only

Update [main.py](main.py) to enforce HTTPS:

```python
# In production, redirect HTTP to HTTPS
if settings.environment == "production":
    app.add_middleware(HTTPSRedirectMiddleware)
```

#### 3. Configure CORS Properly

```python
# main.py
allowed_origins = [
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

#### 4. Set Secure Cookie Attributes

```python
# When setting cookies
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    secure=True,  # HTTPS only
    samesite="lax",
    max_age=3600,
)
```

#### 5. Enable Security Headers

The SecurityHeadersMiddleware is already configured. Verify it's enabled:

```python
# main.py - already configured
app.add_middleware(
    SecurityHeadersMiddleware,
    enable_hsts=True,  # Enable in production
)
```

### Database Security

#### 1. Use Strong Passwords

```bash
# Generate strong database password
openssl rand -base64 24
```

#### 2. Restrict Database Access

PostgreSQL `pg_hba.conf`:
```
# Only allow connections from app servers
host    cms_prod    cms_user    10.0.1.0/24    scram-sha-256
```

#### 3. Enable SSL Connections

```python
# app/database.py
engine = create_async_engine(
    DATABASE_URL,
    connect_args={
        "ssl": "require",  # Require SSL
    }
)
```

#### 4. Regular Backups

```bash
# Daily automated backup
0 2 * * * /usr/local/bin/backup-db.sh
```

### Infrastructure Security

#### 1. Use Firewall Rules

```bash
# Allow only HTTPS and SSH
ufw allow 443/tcp
ufw allow 22/tcp
ufw enable
```

#### 2. Keep System Updated

```bash
# Auto-update security patches
apt-get update && apt-get upgrade -y
```

#### 3. Use Secrets Management

- AWS Secrets Manager
- Azure Key Vault
- Google Secret Manager
- HashiCorp Vault

#### 4. Enable Audit Logging

```python
# app/config.py
LOG_LEVEL = "INFO"  # Production logging
```

## Monitoring & Logging

### Application Monitoring

#### Sentry Integration

```python
# main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

if settings.environment == "production":
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,
        environment=settings.environment,
    )
```

#### Prometheus Metrics

```python
# Add prometheus_fastapi_instrumentator
from prometheus_fastapi_instrumentator import Instrumentator

app = create_app()
Instrumentator().instrument(app).expose(app)
```

### Log Aggregation

#### CloudWatch (AWS)

Configure in ECS task definition:

```json
"logConfiguration": {
  "logDriver": "awslogs",
  "options": {
    "awslogs-group": "/ecs/cms-app",
    "awslogs-region": "us-east-1",
    "awslogs-stream-prefix": "ecs"
  }
}
```

#### ELK Stack (Self-Hosted)

```yaml
# docker-compose.monitoring.yml
services:
  elasticsearch:
    image: elasticsearch:8.10.0
    environment:
      - discovery.type=single-node

  logstash:
    image: logstash:8.10.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf

  kibana:
    image: kibana:8.10.0
    ports:
      - "5601:5601"
```

### Health Checks

The application exposes a `/health` endpoint:

```bash
# Monitor health
curl https://cms.yourdomain.com/health
```

Integrate with monitoring tools:
- AWS CloudWatch Alarms
- Datadog Synthetic Tests
- UptimeRobot
- Pingdom

## Backup & Recovery

### Database Backups

#### Automated Daily Backups

```bash
#!/bin/bash
# /usr/local/bin/backup-db.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/database"
S3_BUCKET="s3://cms-backups/database"

# Create backup
docker-compose exec -T db pg_dump -U cms_user cms_prod | gzip > "$BACKUP_DIR/cms_backup_$DATE.sql.gz"

# Upload to S3
aws s3 cp "$BACKUP_DIR/cms_backup_$DATE.sql.gz" "$S3_BUCKET/"

# Keep only last 30 days locally
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

# Verify backup
if [ $? -eq 0 ]; then
    echo "Backup successful: cms_backup_$DATE.sql.gz"
else
    echo "Backup failed!" | mail -s "DB Backup Failed" admin@yourdomain.com
fi
```

#### Cron Schedule

```bash
# Daily at 2 AM
0 2 * * * /usr/local/bin/backup-db.sh

# Weekly full backup at 3 AM Sunday
0 3 * * 0 /usr/local/bin/backup-db-full.sh
```

### Recovery Procedures

#### Restore from Backup

```bash
# Stop application
docker-compose stop web

# Restore database
gunzip < cms_backup_20260110_020000.sql.gz | docker-compose exec -T db psql -U cms_user cms_prod

# Verify data
docker-compose exec db psql -U cms_user cms_prod -c "SELECT COUNT(*) FROM users;"

# Start application
docker-compose start web
```

## Scaling

### Horizontal Scaling

#### Load Balancer Setup (Nginx)

```nginx
# /etc/nginx/sites-available/cms
upstream cms_backend {
    least_conn;
    server 10.0.1.10:8000 weight=1;
    server 10.0.1.11:8000 weight=1;
    server 10.0.1.12:8000 weight=1;
}

server {
    listen 443 ssl http2;
    server_name cms.yourdomain.com;

    ssl_certificate /etc/ssl/certs/cms.crt;
    ssl_certificate_key /etc/ssl/private/cms.key;

    location / {
        proxy_pass http://cms_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        access_log off;
        proxy_pass http://cms_backend;
    }
}
```

#### Auto-Scaling (AWS)

```bash
# Create auto-scaling policy
aws application-autoscaling register-scalable-target \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/cms-cluster/cms-service \
    --min-capacity 2 \
    --max-capacity 10

aws application-autoscaling put-scaling-policy \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/cms-cluster/cms-service \
    --policy-name cpu75-target-tracking-scaling-policy \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration file://scaling-policy.json
```

### Database Scaling

#### Read Replicas

```python
# app/database.py
from sqlalchemy.ext.asyncio import create_async_engine

# Primary (writes)
primary_engine = create_async_engine(
    settings.database_primary_url,
    pool_size=20,
    max_overflow=10,
)

# Replica (reads)
replica_engine = create_async_engine(
    settings.database_replica_url,
    pool_size=40,
    max_overflow=20,
)
```

#### Connection Pooling

```python
# Optimize connection pool
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,          # Base connection pool
    max_overflow=10,       # Additional overflow connections
    pool_timeout=30,       # Wait timeout
    pool_recycle=3600,     # Recycle connections after 1 hour
    pool_pre_ping=True,    # Verify connections before use
)
```

### Redis Scaling

#### Redis Cluster

```yaml
# docker-compose.redis-cluster.yml
services:
  redis-master:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}

  redis-replica-1:
    image: redis:7-alpine
    command: redis-server --replicaof redis-master 6379 --requirepass ${REDIS_PASSWORD}

  redis-replica-2:
    image: redis:7-alpine
    command: redis-server --replicaof redis-master 6379 --requirepass ${REDIS_PASSWORD}
```

## Post-Deployment Checklist

After deployment, verify:

- [ ] Application health check returns 200
- [ ] Database migrations applied successfully
- [ ] SSL/TLS certificate valid and HTTPS working
- [ ] All environment variables set correctly
- [ ] Logging and monitoring active
- [ ] Backups configured and tested
- [ ] Rate limiting working
- [ ] CORS configured properly
- [ ] Security headers present
- [ ] Error tracking (Sentry) receiving events
- [ ] Load balancer health checks passing
- [ ] DNS records pointing to correct servers
- [ ] Email notifications working (test password reset)
- [ ] Admin user can log in
- [ ] Critical API endpoints responding correctly

## Troubleshooting Production Issues

### Application Not Starting

```bash
# Check logs
docker-compose logs -f web

# Check environment variables
docker-compose exec web env | grep DATABASE_URL

# Test database connection
docker-compose exec web python -c "from app.database import engine; import asyncio; print('DB OK')"
```

### High Response Times

```bash
# Check resource usage
docker stats

# Check database connections
docker-compose exec db psql -U cms_user -c "SELECT count(*) FROM pg_stat_activity;"

# Check Redis
docker-compose exec redis redis-cli -a password INFO stats
```

### Database Connection Pool Exhausted

```python
# Increase pool size in app/database.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=40,      # Increase from 20
    max_overflow=20,   # Increase from 10
)
```

## Support

For deployment issues:
- Review [DOCKER_SETUP.md](DOCKER_SETUP.md) for Docker-specific issues
- Review [MIGRATIONS.md](MIGRATIONS.md) for database issues
- Check application logs: `docker-compose logs -f web`
- Check database logs: `docker-compose logs -f db`

---

Last updated: 2026-01-10
