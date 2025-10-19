"""QueryShield SQLAlchemy Probe

Query performance analysis for FastAPI + SQLAlchemy applications.

Usage:
    from sqlalchemy import create_engine
    from queryshield_sqlalchemy import Recorder, install_probe
    
    engine = create_engine("postgresql://...")
    recorder = Recorder()
    
    with install_probe(engine, recorder):
        # Run queries...
        pass
    
    from queryshield_sqlalchemy import build_report
    report = build_report(recorder, engine)
"""

__version__ = "0.2.0"
__author__ = "QueryShield"
__email__ = "dev@queryshield.io"

from queryshield_sqlalchemy.probe import Recorder, QueryEvent, install_probe
from queryshield_sqlalchemy.report import build_report, write_report

__all__ = [
    "Recorder",
    "QueryEvent",
    "install_probe",
    "build_report",
    "write_report",
]
