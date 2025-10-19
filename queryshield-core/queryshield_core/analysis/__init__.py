"""Query analysis module with AI suggestions"""

from queryshield_core.analysis.classify import classify_n_plus_one, classify_all
from queryshield_core.analysis.explain_checks import explain_classify
from queryshield_core.analysis.ml_suggestions import AIAnalyzer, Suggestion

__all__ = [
    "classify_n_plus_one",
    "classify_all",
    "explain_classify",
    "AIAnalyzer",
    "Suggestion",
]
