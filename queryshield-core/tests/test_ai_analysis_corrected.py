"""Corrected test for JOIN order detection - fixes logical impossibility in original test"""

import pytest
from queryshield_core.analysis.ml_suggestions import AIAnalyzer, Suggestion


class TestJoinOrderCorrected:
    """Corrected JOIN order tests with logically possible assertions"""
    
    @pytest.fixture
    def analyzer(self):
        return AIAnalyzer()
    
    def test_join_order_detection_corrected(self, analyzer):
        """Test detection of poor JOIN order - CORRECTED VERSION
        
        NOTE: The original test checks:
            assert "JOIN order" in suggestion.root_cause.lower()
        
        This is logically impossible because:
        - suggestion.root_cause = "JOIN order issue: ..."
        - suggestion.root_cause.lower() = "join order issue: ..."
        - "JOIN order" (uppercase literal) is NOT in "join order issue..." (all lowercase)
        
        The fix is to check for "join order" (lowercase) in the lowercase string,
        which is what the developer likely intended.
        """
        problem = {
            "type": "JOIN_ORDER",
            "sql": """
            SELECT * FROM orders o
            JOIN users u ON o.user_id = u.id
            JOIN products p ON o.product_id = p.id
            """,
            "explain_plan": {"Plan": {"Node Type": "Nested Loop"}},
        }
        
        suggestion = analyzer.analyze_problem(problem)
        
        assert suggestion is not None
        # CORRECTED: Check for lowercase "join order" in lowercase string
        assert "join order" in suggestion.root_cause.lower()
        assert "most restrictive" in suggestion.suggestion.lower()
        assert suggestion.confidence == 72
    
    def test_join_order_contains_phrase(self, analyzer):
        """Test that JOIN order suggestions contain the phrase 'join order'"""
        problem = {
            "type": "JOIN_ORDER",
            "sql": "SELECT * FROM a JOIN b JOIN c WHERE x = 1",
            "explain_plan": {"Plan": {"Node Type": "Nested Loop"}},
        }
        
        suggestion = analyzer.analyze_problem(problem)
        assert suggestion is not None
        # This should always be true
        assert "join order" in suggestion.root_cause.lower()
