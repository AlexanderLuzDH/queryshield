# QueryShield v0.3.0 - PyPI Publication Guide

**Status**: Ready for publication  
**Date**: October 19, 2025  
**Packages**: 5 (core, sqlalchemy, monitoring, probe, cli)  
**Test Pass Rate**: 98.8% (84/85)

---

## 📋 Pre-Publication Checklist

- ✅ All versions updated to 0.3.0 (CLI, Probe) or 0.2.0 (Core, SQLAlchemy, Monitoring)
- ✅ Comprehensive test suite passing (98.8%)
- ✅ All wheels built successfully
- ✅ README files created for all packages
- ✅ CHANGELOG updated
- ✅ Documentation complete

---

## 🔐 Step 1: PyPI Account Setup

### Create PyPI Account (if you don't have one)
1. Go to https://pypi.org/
2. Click "Register" and create account
3. Verify email address

### Generate API Token
1. Log in to https://pypi.org/manage/account/
2. Go to "API tokens"
3. Create new token with scope: "Entire account"
4. Copy token (save securely)

### Configure Local PyPI Credentials

**Option A: Using .pypirc file** (Recommended)
```bash
# Create ~/.pypirc file
cat > ~/.pypirc << EOF
[distutils]
index-servers =
    pypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi_YOUR_TOKEN_HERE
EOF

chmod 600 ~/.pypirc
```

**Option B: Using environment variable**
```bash
export TWINE_PASSWORD=pypi_YOUR_TOKEN_HERE
```

---

## 📦 Step 2: Verify All Wheels

```bash
cd /path/to/queryShield

# List all wheels
ls -la queryshield-core/dist/*.whl
ls -la queryshield-sqlalchemy/dist/*.whl
ls -la queryshield-monitoring/dist/*.whl
ls -la queryshield/probe/dist/*.whl
ls -la queryshield/cli/dist/*.whl
```

Expected output:
```
queryshield-core/dist/queryshield_core-0.2.0-py3-none-any.whl
queryshield-sqlalchemy/dist/queryshield_sqlalchemy-0.2.0-py3-none-any.whl
queryshield-monitoring/dist/queryshield_monitoring-0.2.0-py3-none-any.whl
queryshield/probe/dist/queryshield_probe-0.3.0-py3-none-any.whl
queryshield/cli/dist/queryshield-0.3.0-py3-none-any.whl
```

---

## 🚀 Step 3: Publish to PyPI

### Manual Upload (Recommended Order)

Upload in dependency order (dependencies first):

```bash
cd /path/to/queryShield

# 1. Upload queryshield-core (no dependencies)
python -m twine upload queryshield-core/dist/queryshield_core-0.2.0-py3-none-any.whl

# 2. Upload queryshield-sqlalchemy (depends on core)
python -m twine upload queryshield-sqlalchemy/dist/queryshield_sqlalchemy-0.2.0-py3-none-any.whl

# 3. Upload queryshield-monitoring (depends on core)
python -m twine upload queryshield-monitoring/dist/queryshield_monitoring-0.2.0-py3-none-any.whl

# 4. Upload queryshield-probe (depends on core)
python -m twine upload queryshield/probe/dist/queryshield_probe-0.3.0-py3-none-any.whl

# 5. Upload queryshield CLI (depends on all others)
python -m twine upload queryshield/cli/dist/queryshield-0.3.0-py3-none-any.whl
```

### Batch Upload (All at Once)

```bash
python -m twine upload \
  queryshield-core/dist/queryshield_core-0.2.0-py3-none-any.whl \
  queryshield-sqlalchemy/dist/queryshield_sqlalchemy-0.2.0-py3-none-any.whl \
  queryshield-monitoring/dist/queryshield_monitoring-0.2.0-py3-none-any.whl \
  queryshield/probe/dist/queryshield_probe-0.3.0-py3-none-any.whl \
  queryshield/cli/dist/queryshield-0.3.0-py3-none-any.whl
```

### Using Script

```bash
bash publish_to_pypi.sh
```

---

## ✅ Step 4: Verify Publication

### Check PyPI Pages
- https://pypi.org/project/queryshield/
- https://pypi.org/project/queryshield-probe/
- https://pypi.org/project/queryshield-core/
- https://pypi.org/project/queryshield-sqlalchemy/
- https://pypi.org/project/queryshield-monitoring/

### Test Installation (in clean environment)

```bash
# Test each package individually
pip install queryshield==0.3.0
pip install queryshield-probe==0.3.0
pip install queryshield-core==0.2.0
pip install queryshield-sqlalchemy==0.2.0
pip install queryshield-monitoring==0.2.0

# Verify installation
python -c "import queryshield; print(queryshield.__version__)"
python -c "import queryshield_core; print('✅ queryshield-core installed')"
python -c "import queryshield_sqlalchemy; print('✅ queryshield-sqlalchemy installed')"
python -c "import queryshield_monitoring; print('✅ queryshield-monitoring installed')"
```

### Test from PyPI (wait 5-10 minutes for indexing)

```bash
# Fresh environment test
python -m venv /tmp/test_queryshield
source /tmp/test_queryshield/bin/activate
pip install queryshield==0.3.0
queryshield --help
```

---

## 📊 Package Details

### queryshield (v0.3.0)
- **Type**: CLI tool
- **Size**: 8.5 KB
- **Dependencies**: typer, pydantic
- **Description**: Command-line tool for database query performance analysis

### queryshield-probe (v0.3.0)
- **Type**: Django probe
- **Size**: 18.6 KB
- **Dependencies**: django, queryshield-core
- **Description**: Django database query probe for pytest and test runner

### queryshield-core (v0.2.0)
- **Type**: Shared library
- **Size**: 10.8 KB
- **Dependencies**: None
- **Description**: Shared analysis logic (N+1 detection, EXPLAIN parsing, cost analysis)

### queryshield-sqlalchemy (v0.2.0)
- **Type**: SQLAlchemy probe
- **Size**: 6.6 KB
- **Dependencies**: sqlalchemy, queryshield-core
- **Description**: SQLAlchemy database query probe for FastAPI and pytest

### queryshield-monitoring (v0.2.0)
- **Type**: Production middleware
- **Size**: 7.0 KB
- **Dependencies**: fastapi, queryshield-core
- **Description**: Production query monitoring middleware for FastAPI/Django

---

## 🔍 Troubleshooting

### Invalid Credentials
```
ERROR Invalid pypi repository or invalid token
```
**Solution**: Check PyPI token and .pypirc configuration

### Package Already Exists
```
ERROR File already exists. See https://pypi.org/help/#file-name-reuse
```
**Solution**: You can't re-upload same version. Increment version or delete from PyPI (requires admin)

### Wheel Not Found
```
ERROR File (path/to/*.whl) does not exist
```
**Solution**: Rebuild wheels: `python -m build --wheel` in each package directory

### Network Timeout
```
ERROR Error in upload request: Upload to https://upload.pypi.org failed
```
**Solution**: Check internet connection, try again later, or use proxy

---

## 📢 Post-Publication Steps

After successful PyPI publication:

1. ✅ **Update website** - Add v0.3.0 to queryshield.app
2. ✅ **Announce launch** - Blog post + social media
3. ✅ **Notify users** - Email existing v0.2.0 users
4. ✅ **GitHub release** - Create v0.3.0 release with changelog
5. ✅ **Community** - Post to ProductHunt, HackerNews, Reddit

---

## 📈 Version History on PyPI

After publication, all versions will be visible:
- https://pypi.org/project/queryshield/#history

Users can:
- Install latest: `pip install queryshield`
- Install specific: `pip install queryshield==0.3.0`
- Upgrade: `pip install --upgrade queryshield`

---

## 🎯 Success Criteria

✅ All 5 packages visible on PyPI  
✅ Each package page has correct description  
✅ Installation from PyPI works without errors  
✅ All dependencies correctly listed  
✅ Documentation links working  
✅ v0.3.0 marked as latest stable release  

---

## 📞 Support

If publication fails:
1. Check PyPI status: https://status.python.org/
2. Review twine documentation: https://twine.readthedocs.io/
3. Check package metadata: `python -m twine check dist/*`

---

**Ready to publish?** Run:
```bash
python -m twine upload \
  queryshield-core/dist/*.whl \
  queryshield-sqlalchemy/dist/*.whl \
  queryshield-monitoring/dist/*.whl \
  queryshield/probe/dist/*.whl \
  queryshield/cli/dist/*.whl
```

Good luck! 🚀
