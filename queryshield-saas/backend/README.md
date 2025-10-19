# QueryShield SaaS Backend API

FastAPI-based backend for QueryShield cloud dashboard. Handles report storage, user management, analysis, and alerting.

## Features

- FastAPI modern async API
- PostgreSQL + SQLAlchemy ORM
- JWT authentication
- Report storage and comparison
- Cost analysis and ROI calculation
- Alert configuration (Slack, GitHub, webhooks)
- Scalable architecture with Redis caching

## Quick Start

### Local Development

**Prerequisites:**
- Python 3.9+
- PostgreSQL 12+
- Redis 5+

**Setup:**

```bash
# Clone and navigate
cd queryshield-saas

# Install dependencies
pip install -e ./backend[dev]

# Create .env file
cp .env.example .env

# Start PostgreSQL and Redis (Docker)
docker-compose up -d postgres redis

# Initialize database
python -m queryshield_saas.database

# Run API server
uvicorn queryshield_saas.main:app --reload
```

API will be available at http://localhost:8000

**Swagger Docs:** http://localhost:8000/docs

### Docker Setup

```bash
# Build and run all services
docker-compose up -d

# Logs
docker-compose logs -f api

# Stop services
docker-compose down
```

## API Endpoints

### Health & Status
- `GET /api/health` - Health check
- `GET /api/ready` - Readiness check (for Kubernetes)

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `POST /api/auth/api-key` - Generate API key for CI/CD

### Reports
- `POST /api/reports` - Upload new report
- `GET /api/reports?org_id=...&limit=20&offset=0` - List organization reports
- `GET /api/reports/{id}` - Get report details
- `POST /api/reports/compare` - Compare two reports
- `GET /api/reports/{id}/trends?days=30` - Get trend data

### Organizations
- `GET /api/organizations/{id}` - Get organization info
- `GET /api/organizations/{id}/members` - List members
- `POST /api/organizations/{id}/members` - Add member

## Database Schema

### Core Tables
- `users` - User accounts with authentication
- `organizations` - Teams/workspaces
- `reports` - QueryShield analysis reports
- `problems` - Detected database issues
- `report_comparisons` - Regression detection
- `alert_configs` - Alert webhooks

## Development

### Running Tests

```bash
pytest tests/ -v --cov=queryshield_saas
```

### Formatting & Linting

```bash
# Format code
black queryshield_saas tests

# Lint
ruff check queryshield_saas tests

# Type checking
mypy queryshield_saas
```

### Database Migrations

Using Alembic (not yet initialized):

```bash
alembic init alembic
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

## Deployment

### AWS EC2 + RDS

```bash
# Build Docker image
docker build -t queryshield-saas:latest .

# Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin <ECR_URL>
docker tag queryshield-saas:latest <ECR_URL>/queryshield-saas:latest
docker push <ECR_URL>/queryshield-saas:latest

# Deploy with ECS, Kubernetes, or Docker Swarm
```

### DigitalOcean App Platform

```bash
# Create app.yaml
# Deploy
doctl apps create --spec app.yaml
```

### Environment Variables

```
DATABASE_URL=postgresql://user:pass@host/db
REDIS_URL=redis://host:6379
SECRET_KEY=your-secret-key
DEBUG=False
```

## API Response Format

### Success Response (200)

```json
{
  "id": "uuid",
  "organization_id": "uuid",
  "queries_total": 50,
  "duration_ms": 2500.5,
  "status": "complete",
  "created_at": "2025-01-15T10:30:00Z"
}
```

### Error Response (4xx/5xx)

```json
{
  "detail": "Error message here",
  "code": "error_code",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## Performance Targets

- Report upload: < 1s
- Report list: < 500ms (cached after 60s)
- Comparison: < 2s
- Dashboard queries: < 200ms (with Redis)

## Monitoring

- Sentry integration for error tracking
- Health checks every 30s
- Database connection pooling (10 connections)
- Redis cache for dashboard queries

## TODOs

- [ ] Implement authentication endpoints (register, login, JWT)
- [ ] Implement report storage and retrieval
- [ ] Implement comparison logic
- [ ] Implement alert webhooks
- [ ] Add Stripe integration
- [ ] Add email notifications
- [ ] Add database migrations with Alembic
- [ ] Add comprehensive test suite
- [ ] Add API rate limiting
- [ ] Add request logging and monitoring

## License

MIT - See LICENSE file
