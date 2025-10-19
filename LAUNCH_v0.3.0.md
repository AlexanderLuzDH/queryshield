# QueryShield v0.3.0 Launch Package

**Ship Date:** This Week (5 days)  
**Target:** PyPI + SaaS deployment + community announcement  
**Goal:** Get real users, gather feedback, iterate toward v0.4.0

---

## 📋 Pre-Launch Checklist (48 Hours)

### Code Quality
- [ ] Run full test suite across all packages
- [ ] Check coverage: target 80%+ per package
- [ ] Lint all Python code (mypy, black, ruff)
- [ ] Update CHANGELOG.md with Phase 2 features
- [ ] Bump versions: `0.3.0` (remove -rc)

### Documentation
- [ ] Update main README.md with all Phase 2 features
- [ ] Add "What's New in v0.3.0" section
- [ ] Verify all links in docs (no 404s)
- [ ] Add FASTAPI_SQLALCHEMY_GUIDE.md to PyPI package
- [ ] Add PRODUCTION_MONITORING.md to PyPI package

### Packages to Publish
```
1. queryshield-core==0.2.0      (foundation)
2. queryshield-sqlalchemy==0.2.0 (FastAPI)
3. queryshield-monitoring==0.2.0 (production)
4. queryshield-probe==0.3.0      (Django - existing)
5. queryshield==0.3.0            (CLI - main)
6. queryshield-action==0.3.0     (GitHub)
```

### SaaS Deployment
- [ ] Deploy production_queries tables
- [ ] Deploy alert_rules tables
- [ ] Deploy webhook_configs tables
- [ ] Test Slack integration with test webhook
- [ ] Verify GitHub Checks API integration
- [ ] Database migrations on production
- [ ] Update SaaS homepage with v0.3 features

---

## 🚀 Launch Day Tasks (Day 1)

### 8 AM: Final Pre-Launch
```bash
# Run everything one more time
pytest --cov=queryshield_core tests/
pytest --cov=queryshield_sqlalchemy tests/
pytest --cov=queryshield_monitoring tests/

# Build packages
python -m build queryshield-core/
python -m build queryshield-sqlalchemy/
python -m build queryshield-monitoring/
python -m build queryshield/
```

### 9 AM: Publish to PyPI (requires credentials)
```bash
# Publish in order (dependencies first)
twine upload queryshield-core/dist/*
twine upload queryshield-sqlalchemy/dist/*
twine upload queryshield-monitoring/dist/*
twine upload queryshield/dist/*
twine upload queryshield-action/dist/*
```

### 10 AM: Deploy SaaS
```bash
# SSH to production server
ssh user@queryshield.io

# Deploy backend
git pull
docker-compose build
docker-compose up -d

# Verify
curl https://api.queryshield.app/api/health
```

### 11 AM: Verify Everything Works
- [ ] Install from PyPI: `pip install queryshield==0.3.0`
- [ ] Test Django probe: `queryshield analyze --runner django`
- [ ] Test FastAPI probe: `pytest -p queryshield_sqlalchemy.runners.pytest_plugin`
- [ ] Test production monitor: `queryshield production-monitor status`
- [ ] Verify SaaS dashboard loads
- [ ] Test Slack webhook (send test alert)
- [ ] Test GitHub Checks API (submit dummy check)

### 12 PM: Community Announcements

#### Twitter/X Thread
```
🚀 QueryShield v0.3.0 is LIVE!

Multi-framework ORM performance analysis:
✅ Django (since v0.1)
✅ FastAPI + SQLAlchemy (NEW!)
✅ Production Monitoring (NEW!)

Detect N+1 queries, missing indexes, and regressions 
before they hit production.

pip install queryshield==0.3.0

Read more → [blog link]
```

#### GitHub Release
```markdown
# v0.3.0: Multi-Framework Support + Production Monitoring

## What's New

### 🎉 FastAPI + SQLAlchemy Support
- Complete queryshield-sqlalchemy package
- SQLAlchemy event hooks for automatic query capture
- pytest plugin for integration tests
- Example app with N+1 demonstrations

### 🔍 Production Query Monitoring
- queryshield-monitoring middleware
- 1% intelligent sampling (zero overhead)
- Automatic regression detection
- Slack alerts + GitHub Checks

### 🧠 AI Root Cause Analysis
- 8 detection rules with confidence scoring
- Code examples for fixes (Django + SQLAlchemy)
- Hotspot detection

### 🔗 Integrations
- Slack webhooks with formatted alerts
- GitHub Checks API (more prominent than comments)
- Webhook configuration in SaaS

## Installation

```bash
# Django users (existing functionality)
pip install queryshield==0.3.0

# FastAPI users (NEW)
pip install queryshield-sqlalchemy==0.2.0

# Production monitoring (NEW)
pip install queryshield-monitoring==0.2.0
```

## Documentation
- [FastAPI Integration Guide](https://github.com/queryshield/queryshield/blob/main/FASTAPI_SQLALCHEMY_GUIDE.md)
- [Production Monitoring Setup](https://github.com/queryshield/queryshield/blob/main/PRODUCTION_MONITORING.md)
- [Full Changelog](https://github.com/queryshield/queryshield/blob/main/CHANGELOG.md)
```

#### Blog Post (500 words)
```markdown
# QueryShield v0.3.0: From Django Testing to Production Intelligence

Today we're excited to announce QueryShield v0.3.0, 
our biggest release yet! 🚀

## The Problem

Database query performance problems are notoriously hard to catch:
- N+1 queries that work fine in tests but crush production
- Missing indexes that only show up under load
- Performance regressions between deploys

Most tools focus on production monitoring AFTER the damage is done.
QueryShield shifts left - catching problems in tests.

## What's New in v0.3.0

### Multi-Framework Support
We've extracted our core analysis logic into queryshield-core,
enabling analysis across frameworks:

- **Django**: Since v0.1 (now v0.3)
- **FastAPI + SQLAlchemy**: New! hooks into SQLAlchemy events
- **Production Apps**: New! 1% sampling middleware

### Production Intelligence
The real innovation: intelligent sampling in production

```python
# Add to your FastAPI app
from queryshield_monitoring import install_queryshield_fastapi

config = MonitoringConfig.from_env()
install_queryshield_fastapi(app, engine, config)
```

Now your production app captures 1% of queries, batches them,
and uploads to our SaaS. Zero performance impact.

### AI-Powered Analysis
When problems are detected, we don't just flag them.
We explain them:

"95% confident N+1 problem: Loop accesses author FK without prefetch.
Fix: Use joinedload(). Expected improvement: 10x faster."

### Integration Stack
- **Slack**: Real-time alerts with fixes
- **GitHub**: Checks API blocks merges on violations
- **SaaS Dashboard**: Full analytics + trends

## Getting Started

### For Django Users (Existing)
```bash
pip install queryshield==0.3.0
queryshield analyze --runner django --explain
```

### For FastAPI Users (New!)
```bash
pip install queryshield-sqlalchemy
pytest tests/ -p queryshield_sqlalchemy.runners.pytest_plugin
```

### For Production (New!)
```bash
pip install queryshield-monitoring
# Add to your FastAPI/Django app
# See: https://docs.queryshield.io/production-monitoring
```

## What's Next

We're in active development on v0.4.0:
- VS Code extension (inline annotations)
- Advanced analytics dashboard
- Query timeline + cost breakdown

We're also [looking for early enterprise customers](https://queryshield.io)
for v1.0 on-premise deployment.

## Community

- GitHub: https://github.com/queryshield/queryshield
- Discord: https://discord.gg/queryshield
- Docs: https://docs.queryshield.io

Join us! We're building the future of ORM performance analysis.

---

*QueryShield is open-source (MIT) with an optional SaaS dashboard.*
*Free tier on pypi, Pro tier at $99/mo, Enterprise tier available.*
```

#### HackerNews Post
```
title: "QueryShield v0.3.0 – Catch Database Regressions in Django/FastAPI Tests"
text: "Multi-framework ORM performance analysis. 
Detect N+1 queries, missing indexes, regressions. 
Production monitoring with 1% sampling. 
Now with AI root cause analysis. 
https://github.com/queryshield/queryshield"
```

#### ProductHunt (Optional, Day 2)
- [ ] Create ProductHunt listing
- [ ] Prepare 3-5 screenshots of dashboard
- [ ] Write compelling description
- [ ] Schedule for morning launch

---

## 📊 Post-Launch (Days 2-5)

### Community Engagement
- [ ] Monitor GitHub Issues for bugs
- [ ] Respond to all tweets/comments within 1 hour
- [ ] Track PyPI download stats
- [ ] Collect user feedback via GitHub Discussions

### Quick Fixes (If Needed)
- [ ] Patch any critical bugs
- [ ] Release v0.3.1 if necessary (hotfix)
- [ ] Update docs based on user questions

### Metrics to Track
- [ ] PyPI downloads in first week (target: 500+)
- [ ] GitHub stars (target: +50)
- [ ] SaaS signups (target: 10+)
- [ ] Twitter impressions (target: 5K+)
- [ ] Slack community joins (target: 20+)

---

## 🎯 Success Criteria for v0.3.0 Launch

✅ **Technical**
- All tests passing
- 0 critical bugs in first week
- API availability >99.5%

✅ **Community**
- 500+ PyPI downloads in week 1
- 50+ GitHub stars
- 10+ SaaS signups
- 5+ positive feedback comments

✅ **Market**
- Feature in 2+ Python newsletters
- 1+ mention in dev communities
- Interest from 2+ FastAPI companies

---

## 📝 Version Numbers After Launch

After v0.3.0 ships:

```
CURRENT (v0.3.0):
  queryshield==0.3.0
  queryshield-core==0.2.0
  queryshield-sqlalchemy==0.2.0
  queryshield-monitoring==0.2.0
  queryshield-action==0.3.0

NEXT (v0.4.0-beta):
  - VS Code extension added
  - Analytics dashboard beta

FUTURE (v0.4.0):
  - Production ready
  - Slack fully integrated

FUTURE (v1.0.0):
  - On-premise option
  - RBAC + audit logging
```

---

## 🔥 Post-Launch Phase 3 Sprint (Weeks 2-4)

After launch, iterate with real users:

- **Week 2**: Gather feedback, patch bugs, add top-requested features
- **Week 3**: Build Phase 3.4 (VS Code extension with user insights)
- **Week 4**: Build Phase 3.5 (analytics dashboard based on usage)

**Estimated v0.4.0-beta release: Week 4**
**Estimated v0.4.0 stable release: Week 5**

---

## Questions Before Launch?

- Is SaaS deployment infrastructure ready? (check security groups, SSL certs)
- Do we have PyPI account credentials? (check .pypirc)
- Have we tested all integrations in staging?
- Is the blog post ready to publish?

**GO LIVE!** 🚀
