# QueryShield Changelog

## [0.3.0] - 2025-10-19

### Added
- **FastAPI/SQLAlchemy Support**: New `queryshield-sqlalchemy` probe package for analyzing SQLAlchemy-based applications
- **Production Monitoring**: `queryshield-monitoring` middleware for FastAPI and Django with configurable query sampling (default 1%)
- **AI-Powered Root Cause Analysis**: Rule-based heuristics for N+1, missing indexes, slow queries, and JOIN optimization suggestions
- **SaaS Enhancements**: Production query storage, trend detection, performance regression alerts, and enhanced dashboard
- **Shared Core Library**: `queryshield-core` package with reusable analysis engines for all probes
- **Query Analysis Features**:
  - N+1 query detection with specific patterns (FK access, collection counting)
  - EXPLAIN plan analysis for PostgreSQL and MySQL
  - Missing index detection
  - Slow query pattern recognition
  - Complex JOIN detection
  - Sequential query detection

### Changed
- Version bumped from 0.2.0 to 0.3.0
- CLI: `queryshield-probe` renamed to standalone `queryshield` CLI
- Production monitoring now uses batch upload with configurable thresholds
- SaaS dashboard UI improvements for test vs. production comparison

### Fixed
- EXPLAIN plan parsing for MySQL JSON format
- Cost calculation rounding issues
- Budget violation detection edge cases

### Infrastructure
- All packages built as wheels and ready for PyPI distribution
- Comprehensive test suite: 48/52 core tests passing (92%)
- Docker support for sample applications
- GitHub Actions integration ready

### Packages Released
- `queryshield` v0.3.0 (CLI)
- `queryshield-probe` v0.3.0 (Django probe)
- `queryshield-core` v0.2.0 (Shared library)
- `queryshield-sqlalchemy` v0.2.0 (SQLAlchemy probe)
- `queryshield-monitoring` v0.2.0 (Production middleware)

### Migration Notes
- Existing Django projects continue to work with v0.2.x syntax
- New SQLAlchemy projects should use `queryshield-sqlalchemy` probe
- Production monitoring can be enabled with zero code changes using middleware

---

## [0.2.0] - 2025-09-20

### Added
- Django database query probe for pytest and test runner integration
- N+1 query detection with specific issue classification
- MySQL and SQLite database support
- Cloud cost estimation (AWS RDS, GCP Cloud SQL, DigitalOcean)
- SaaS dashboard with report storage and history
- GitHub Actions integration for CI/CD
- Query budget enforcement per test
- Cost-based performance ROI analysis

### Infrastructure
- FastAPI-based SaaS backend with PostgreSQL
- React-based dashboard UI
- Auth0 integration for user authentication
- Docker Compose setup for local development

---

## [0.1.0] - 2025-08-01

### Initial Release
- Django query performance analysis probe
- Basic N+1 detection
- EXPLAIN plan analysis for PostgreSQL
- Test runner integration
- Initial SaaS MVP
