"""Tests for AI root cause analysis"""

import pytest
from queryshield_core.analysis.ml_suggestions import AIAnalyzer, Suggestion


class TestAIAnalyzer:
    """Tests for AI root cause analyzer"""
    
    @pytest.fixture
    def analyzer(self):
        return AIAnalyzer()
    
    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initializes with all rules"""
        assert len(analyzer.patterns) == 8  # 8 rules registered
    
    # N+1 Detection Tests
    
    def test_nplus1_foreign_key_detection(self, analyzer):
        """Test detection of N+1 foreign key access"""
        problem = {
            "type": "N+1",
            "sql": "SELECT * FROM books WHERE id = ?",
            "count": 10,
        }
        
        suggestion = analyzer.analyze_problem(problem)
        
        assert suggestion is not None
        assert "Loop iterates collection" in suggestion.root_cause
        assert "joinedload" in suggestion.suggestion.lower()
        assert suggestion.confidence == 95
        assert "10x faster" in suggestion.estimated_improvement
    
    def test_nplus1_count_detection(self, analyzer):
        """Test detection of N+1 count queries"""
        problem = {
            "type": "N+1",
            "sql": "SELECT COUNT(*) FROM books WHERE author_id = ?",
            "count": 5,
        }
        
        suggestion = analyzer.analyze_problem(problem)
        
        assert suggestion is not None
        assert "Counting related items" in suggestion.root_cause
        assert "annotate" in suggestion.suggestion.lower() or "annotated" in suggestion.suggestion.lower()
        assert suggestion.confidence >= 80
    
    # Index Detection Tests
    
    def test_missing_index_detection(self, analyzer):
        """Test detection of missing indexes"""
        problem = {
            "type": "MISSING_INDEX",
            "sql": "SELECT * FROM users WHERE email = ?",
        }
        
        suggestion = analyzer.analyze_problem(problem)
        
        assert suggestion is not None
        assert "email" in suggestion.root_cause.lower()
        assert "CREATE INDEX" in suggestion.suggestion
        assert "idx_email" in suggestion.code_example
        assert suggestion.confidence == 90
    
    # Slow Query Tests
    
    def test_slow_query_select_star(self, analyzer):
        """Test detection of SELECT * as performance issue"""
        problem = {
            "type": "SLOW_QUERY",
            "sql": "SELECT * FROM users",
            "duration_ms": 500,
        }
        
        suggestion = analyzer.analyze_problem(problem)
        
        assert suggestion is not None
        assert "SELECT *" in suggestion.root_cause
        assert "unnecessary columns" in suggestion.root_cause.lower()
        assert suggestion.confidence == 70
    
    def test_complex_join_detection(self, analyzer):
        """Test detection of complex queries with many JOINs"""
        problem = {
            "type": "SLOW_QUERY",
            "sql": """
            SELECT * FROM orders o
            JOIN users u ON o.user_id = u.id
            JOIN products p ON o.product_id = p.id
            JOIN categories c ON p.category_id = c.id
            """,
            "duration_ms": 1000,
        }
        
        suggestion = analyzer.analyze_problem(problem)
        
        assert suggestion is not None
        assert "3 JOINs" in suggestion.root_cause
        assert suggestion.confidence == 65
    
    # Sequential Scan Tests
    
    def test_seq_scan_detection(self, analyzer):
        """Test detection of sequential scans"""
        problem = {
            "type": "SEQ_SCAN",
            "sql": "SELECT * FROM users",
            "explain_plan": {"Plan": {"Node Type": "Seq Scan", "Relation Name": "users"}},
        }
        
        suggestion = analyzer.analyze_problem(problem)
        
        assert suggestion is not None
        assert "Sequential scan" in suggestion.root_cause
        assert suggestion.confidence == 85
        assert "50-1000x faster" in suggestion.estimated_improvement
    
    # Sort Tests
    
    def test_sort_without_index_detection(self, analyzer):
        """Test detection of sorts without indexes"""
        problem = {
            "type": "SORT",
            "sql": "SELECT * FROM users ORDER BY email",
            "explain_plan": {"Plan": {"Node Type": "Sort"}},
        }
        
        suggestion = analyzer.analyze_problem(problem)
        
        assert suggestion is not None
        assert "expensive in-memory sort" in suggestion.root_cause.lower()
        assert "CREATE INDEX" in suggestion.suggestion
        assert suggestion.confidence == 88
    
    # Sequential Queries Tests
    
    def test_sequential_queries_detection(self, analyzer):
        """Test detection of sequential query patterns"""
        problem = {
            "type": "SEQUENTIAL_QUERIES",
            "count": 5,
        }
        
        suggestion = analyzer.analyze_problem(problem)
        
        assert suggestion is not None
        assert "sequential" in suggestion.root_cause.lower()
        assert "Batch queries" in suggestion.suggestion
        assert suggestion.confidence == 75
    
    # Table Scan Tests
    
    def test_like_without_fulltext(self, analyzer):
        """Test detection of LIKE without full-text index"""
        problem = {
            "type": "TABLE_SCAN",
            "sql": "SELECT * FROM users WHERE name LIKE ?",
        }
        
        suggestion = analyzer.analyze_problem(problem)
        
        assert suggestion is not None
        assert "LIKE query" in suggestion.root_cause
        assert "full-text" in suggestion.suggestion.lower()
        assert suggestion.confidence == 70
    
    # JOIN Order Tests
    
    def test_join_order_detection(self, analyzer):
        """Test detection of poor JOIN order"""
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
        assert "JOIN order" in suggestion.root_cause.lower()
        assert "most restrictive" in suggestion.suggestion.lower()
        assert suggestion.confidence == 72
    
    # Insight Generation Tests
    
    def test_generate_insights_empty_problems(self):
        """Test generating insights from empty problem list"""
        insights = AIAnalyzer.generate_insights([])
        
        assert insights["problems_analyzed"] == 0
        assert insights["suggestions"] == []
        assert insights["hotspots"] == []
        assert insights["confidence_score"] == 0
    
    def test_generate_insights_single_problem(self):
        """Test generating insights from single problem"""
        problems = [
            {
                "type": "N+1",
                "sql": "SELECT * FROM books WHERE id = ?",
                "count": 10,
            }
        ]
        
        insights = AIAnalyzer.generate_insights(problems)
        
        assert insights["problems_analyzed"] == 1
        assert len(insights["suggestions"]) == 1
        assert insights["suggestions"][0]["confidence"] == 95
        assert insights["confidence_score"] == 95
    
    def test_generate_insights_multiple_problems(self):
        """Test generating insights from multiple problems"""
        problems = [
            {
                "type": "N+1",
                "sql": "SELECT * FROM books WHERE id = ?",
                "count": 10,
            },
            {
                "type": "MISSING_INDEX",
                "sql": "SELECT * FROM users WHERE email = ?",
            },
            {
                "type": "SLOW_QUERY",
                "sql": "SELECT * FROM orders",
                "duration_ms": 500,
            },
        ]
        
        insights = AIAnalyzer.generate_insights(problems)
        
        assert insights["problems_analyzed"] == 3
        assert len(insights["suggestions"]) == 3
        assert insights["confidence_score"] > 0  # Average of scores
        assert insights["optimization_potential"] >= 0
    
    def test_generate_insights_hotspot_detection(self):
        """Test detection of hotspots in insights"""
        problems = [
            {
                "type": "N+1",
                "sql": "SELECT * FROM books WHERE id = ?",
                "count": 20,  # High frequency
            }
        ]
        
        insights = AIAnalyzer.generate_insights(problems)
        
        assert len(insights["hotspots"]) > 0
        hotspot = insights["hotspots"][0]
        assert hotspot["type"] == "N+1"
        assert hotspot["frequency"] == 20
        assert hotspot["severity"] == "HIGH"
    
    def test_no_suggestion_for_unknown_problem(self, analyzer):
        """Test that unknown problem types return None"""
        problem = {
            "type": "UNKNOWN_TYPE",
            "sql": "SELECT * FROM users",
        }
        
        suggestion = analyzer.analyze_problem(problem)
        
        assert suggestion is None
    
    def test_suggestion_structure(self, analyzer):
        """Test structure of suggestion object"""
        problem = {
            "type": "N+1",
            "sql": "SELECT * FROM books WHERE id = ?",
            "count": 5,
        }
        
        suggestion = analyzer.analyze_problem(problem)
        
        assert isinstance(suggestion, Suggestion)
        assert isinstance(suggestion.root_cause, str)
        assert isinstance(suggestion.suggestion, str)
        assert isinstance(suggestion.confidence, int)
        assert 0 <= suggestion.confidence <= 100
        assert isinstance(suggestion.estimated_improvement, str)
        assert isinstance(suggestion.similar_patterns, int)


class TestSuggestionDataclass:
    """Tests for Suggestion dataclass"""
    
    def test_suggestion_creation(self):
        """Test creating suggestion object"""
        sugg = Suggestion(
            root_cause="Test cause",
            suggestion="Test fix",
            confidence=85,
        )
        
        assert sugg.root_cause == "Test cause"
        assert sugg.suggestion == "Test fix"
        assert sugg.confidence == 85
        assert sugg.code_example is None
    
    def test_suggestion_with_all_fields(self):
        """Test suggestion with all optional fields"""
        sugg = Suggestion(
            root_cause="Test cause",
            suggestion="Test fix",
            code_example="code",
            confidence=85,
            estimated_improvement="50x faster",
            similar_patterns=10,
        )
        
        assert sugg.code_example == "code"
        assert sugg.estimated_improvement == "50x faster"
        assert sugg.similar_patterns == 10
    
    def test_suggestion_default_values(self):
        """Test suggestion default values"""
        sugg = Suggestion(
            root_cause="Test",
            suggestion="Fix",
        )
        
        assert sugg.code_example is None
        assert sugg.confidence == 50
        assert sugg.estimated_improvement == ""
        assert sugg.similar_patterns == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
