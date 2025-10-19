"""Extended comprehensive tests for AI root cause analysis

Testing edge cases, stress scenarios, and difficult patterns.
"""

import pytest
from queryshield_core.analysis.ml_suggestions import AIAnalyzer, Suggestion


class TestEdgeCases:
    """Edge case tests for robustness"""
    
    @pytest.fixture
    def analyzer(self):
        return AIAnalyzer()
    
    # Empty/Null Cases
    
    def test_empty_problem_dict(self, analyzer):
        """Test handling of empty problem dict"""
        result = analyzer.analyze_problem({})
        assert result is None
    
    def test_missing_type_field(self, analyzer):
        """Test problem without type field"""
        result = analyzer.analyze_problem({"sql": "SELECT * FROM users"})
        assert result is None
    
    def test_none_sql_field(self, analyzer):
        """Test problem with None SQL"""
        result = analyzer.analyze_problem({"type": "N+1", "sql": None})
        assert result is None
    
    def test_empty_sql_string(self, analyzer):
        """Test problem with empty SQL string"""
        result = analyzer.analyze_problem({"type": "SLOW_QUERY", "sql": ""})
        assert result is None
    
    # N+1 Edge Cases
    
    def test_nplus1_with_zero_count(self, analyzer):
        """Test N+1 with zero repetitions"""
        problem = {
            "type": "N+1",
            "sql": "SELECT * FROM books WHERE id = ?",
            "count": 0,
        }
        suggestion = analyzer.analyze_problem(problem)
        # Should still detect the pattern even with 0 count
        assert suggestion is not None
    
    def test_nplus1_with_very_high_count(self, analyzer):
        """Test N+1 with 1000+ repetitions"""
        problem = {
            "type": "N+1",
            "sql": "SELECT * FROM books WHERE id = ?",
            "count": 10000,
        }
        suggestion = analyzer.analyze_problem(problem)
        assert suggestion is not None
        assert "10000x faster" in suggestion.estimated_improvement
    
    def test_nplus1_lowercase_sql(self, analyzer):
        """Test N+1 detection with lowercase SQL"""
        problem = {
            "type": "N+1",
            "sql": "select * from books where id = ?",
            "count": 5,
        }
        suggestion = analyzer.analyze_problem(problem)
        # Should still detect even with lowercase
        assert suggestion is not None
    
    # EXPLAIN Plan Edge Cases
    
    def test_seq_scan_nested_deep(self, analyzer):
        """Test sequential scan in deeply nested EXPLAIN plan"""
        problem = {
            "type": "N+1",
            "sql": "SELECT * FROM books WHERE id = ?",
            "count": 5,
            "explain_plan": {
                "Plan": {
                    "Node Type": "Nested Loop",
                    "Plans": [
                        {
                            "Node Type": "Seq Scan",
                            "Relation Name": "books"
                        }
                    ]
                }
            }
        }
        suggestion = analyzer.analyze_problem(problem)
        assert suggestion is not None
    
    def test_complex_join_with_subqueries(self, analyzer):
        """Test complex query with subqueries and CTEs"""
        problem = {
            "type": "SLOW_QUERY",
            "sql": """
            WITH user_orders AS (
                SELECT user_id, COUNT(*) as order_count
                FROM orders o
                JOIN customers c ON o.customer_id = c.id
                JOIN products p ON o.product_id = p.id
                JOIN categories cat ON p.category_id = cat.id
                WHERE c.country = 'US'
                GROUP BY user_id
            )
            SELECT * FROM user_orders
            """,
            "duration_ms": 2000,
        }
        suggestion = analyzer.analyze_problem(problem)
        assert suggestion is not None
        assert "4 JOINs" in suggestion.root_cause or "complex" in suggestion.root_cause.lower()
    
    # Missing Index Edge Cases
    
    def test_missing_index_compound_where(self, analyzer):
        """Test missing index with compound WHERE clause"""
        problem = {
            "type": "MISSING_INDEX",
            "sql": "SELECT * FROM users WHERE email = ? AND status = ? AND created_at > ?",
        }
        suggestion = analyzer.analyze_problem(problem)
        assert suggestion is not None
        assert "email" in suggestion.root_cause.lower()
    
    def test_missing_index_in_join(self, analyzer):
        """Test missing index in JOIN condition"""
        problem = {
            "type": "MISSING_INDEX",
            "sql": "SELECT * FROM orders o JOIN users u ON o.user_id = u.id WHERE u.email = ?",
        }
        suggestion = analyzer.analyze_problem(problem)
        assert suggestion is not None
    
    # Slow Query Edge Cases
    
    def test_slow_query_very_fast(self, analyzer):
        """Test query marked as slow but fast (edge case)"""
        problem = {
            "type": "SLOW_QUERY",
            "sql": "SELECT * FROM users",
            "duration_ms": 1,
        }
        suggestion = analyzer.analyze_problem(problem)
        # May or may not return, but should not crash
        assert isinstance(suggestion, (Suggestion, type(None)))
    
    def test_slow_query_extremely_slow(self, analyzer):
        """Test extremely slow query (60 seconds)"""
        problem = {
            "type": "SLOW_QUERY",
            "sql": "SELECT * FROM huge_table",
            "duration_ms": 60000,
        }
        suggestion = analyzer.analyze_problem(problem)
        assert suggestion is not None
    
    # Sequential Queries
    
    def test_sequential_queries_single(self, analyzer):
        """Test single sequential query (below threshold)"""
        problem = {
            "type": "SEQUENTIAL_QUERIES",
            "count": 1,
        }
        suggestion = analyzer.analyze_problem(problem)
        # Should not trigger, as minimum is 3
        assert suggestion is None
    
    def test_sequential_queries_many(self, analyzer):
        """Test many sequential queries (50+)"""
        problem = {
            "type": "SEQUENTIAL_QUERIES",
            "count": 100,
        }
        suggestion = analyzer.analyze_problem(problem)
        assert suggestion is not None
        assert "100x faster" in suggestion.estimated_improvement


class TestDifficultPatterns:
    """Tests for difficult and complex query patterns"""
    
    @pytest.fixture
    def analyzer(self):
        return AIAnalyzer()
    
    def test_json_functions_in_where(self, analyzer):
        """Test queries with JSON functions in WHERE"""
        problem = {
            "type": "SLOW_QUERY",
            "sql": "SELECT * FROM users WHERE data->'settings'->>'theme' = 'dark'",
            "duration_ms": 800,
        }
        suggestion = analyzer.analyze_problem(problem)
        # May not have specific rule, but should not crash
        assert isinstance(suggestion, (Suggestion, type(None)))
    
    def test_window_functions(self, analyzer):
        """Test queries with window functions"""
        problem = {
            "type": "SLOW_QUERY",
            "sql": """
            SELECT user_id,
                   order_total,
                   SUM(order_total) OVER (PARTITION BY user_id ORDER BY created_at) as running_total
            FROM orders
            """,
            "duration_ms": 1500,
        }
        suggestion = analyzer.analyze_problem(problem)
        assert isinstance(suggestion, (Suggestion, type(None)))
    
    def test_union_queries(self, analyzer):
        """Test UNION queries with multiple SELECTs"""
        problem = {
            "type": "SLOW_QUERY",
            "sql": """
            SELECT id, name, 'user' as type FROM users
            UNION
            SELECT id, name, 'admin' as type FROM admins
            UNION
            SELECT id, name, 'guest' as type FROM guests
            """,
            "duration_ms": 2000,
        }
        suggestion = analyzer.analyze_problem(problem)
        assert isinstance(suggestion, (Suggestion, type(None)))
    
    def test_recursive_cte(self, analyzer):
        """Test recursive CTE queries"""
        problem = {
            "type": "SLOW_QUERY",
            "sql": """
            WITH RECURSIVE hierarchy AS (
                SELECT id, parent_id, name, 1 as depth FROM categories WHERE parent_id IS NULL
                UNION ALL
                SELECT c.id, c.parent_id, c.name, h.depth + 1
                FROM categories c
                JOIN hierarchy h ON c.parent_id = h.id
                WHERE h.depth < 10
            )
            SELECT * FROM hierarchy
            """,
            "duration_ms": 5000,
        }
        suggestion = analyzer.analyze_problem(problem)
        assert isinstance(suggestion, (Suggestion, type(None)))
    
    def test_cross_join_potential(self, analyzer):
        """Test queries that might trigger cartesian product"""
        problem = {
            "type": "SLOW_QUERY",
            "sql": """
            SELECT * FROM users u
            JOIN orders o
            JOIN products p
            WHERE u.status = 'active'
            """,
            "duration_ms": 10000,
            "explain_plan": {"Plan": {"Node Type": "Nested Loop"}},
        }
        suggestion = analyzer.analyze_problem(problem)
        assert suggestion is not None


class TestInsightGeneration:
    """Tests for generating insights from multiple problems"""
    
    def test_insights_with_many_problems(self):
        """Test insight generation with 50 problems"""
        problems = [
            {
                "type": "N+1",
                "sql": f"SELECT * FROM books WHERE id = {i}",
                "count": i,
            }
            for i in range(1, 51)
        ]
        
        insights = AIAnalyzer.generate_insights(problems)
        
        assert insights["problems_analyzed"] == 50
        assert len(insights["suggestions"]) == 50
        assert insights["confidence_score"] > 0
    
    def test_insights_mixed_problem_types(self):
        """Test insights with diverse problem types"""
        problems = [
            {"type": "N+1", "sql": "SELECT * FROM books WHERE id = ?", "count": 10},
            {"type": "MISSING_INDEX", "sql": "SELECT * FROM users WHERE email = ?"},
            {"type": "SLOW_QUERY", "sql": "SELECT * FROM orders", "duration_ms": 1000},
            {"type": "SEQ_SCAN", "sql": "SELECT * FROM users", "explain_plan": {"Plan": {"Node Type": "Seq Scan", "Relation Name": "users"}}},
            {"type": "SEQUENTIAL_QUERIES", "count": 5},
            {"type": "TABLE_SCAN", "sql": "SELECT * FROM users WHERE name LIKE ?"},
        ]
        
        insights = AIAnalyzer.generate_insights(problems)
        
        assert insights["problems_analyzed"] == 6
        assert len(insights["suggestions"]) >= 5
    
    def test_insights_hotspot_ranking(self):
        """Test that hotspots are ranked by severity"""
        problems = [
            {"type": "N+1", "sql": "SELECT * FROM books WHERE id = ?", "count": 100},
            {"type": "N+1", "sql": "SELECT * FROM authors WHERE id = ?", "count": 10},
            {"type": "MISSING_INDEX", "sql": "SELECT * FROM users WHERE email = ?"},
        ]
        
        insights = AIAnalyzer.generate_insights(problems)
        
        assert len(insights["hotspots"]) > 0
        # Highest frequency should be first
        if len(insights["hotspots"]) > 1:
            assert insights["hotspots"][0]["frequency"] >= insights["hotspots"][1]["frequency"]


class TestSuggestionQuality:
    """Tests for suggestion quality and correctness"""
    
    @pytest.fixture
    def analyzer(self):
        return AIAnalyzer()
    
    def test_suggestion_has_all_fields(self, analyzer):
        """Test that all suggestions have required fields"""
        problem = {
            "type": "N+1",
            "sql": "SELECT * FROM books WHERE id = ?",
            "count": 5,
        }
        suggestion = analyzer.analyze_problem(problem)
        
        assert suggestion is not None
        assert hasattr(suggestion, 'root_cause')
        assert hasattr(suggestion, 'suggestion')
        assert hasattr(suggestion, 'confidence')
        assert hasattr(suggestion, 'estimated_improvement')
        assert hasattr(suggestion, 'similar_patterns')
        assert hasattr(suggestion, 'code_example')
    
    def test_confidence_bounds(self, analyzer):
        """Test that confidence is always 0-100"""
        test_cases = [
            {"type": "N+1", "sql": "SELECT * FROM books WHERE id = ?", "count": 5},
            {"type": "MISSING_INDEX", "sql": "SELECT * FROM users WHERE email = ?"},
            {"type": "SLOW_QUERY", "sql": "SELECT * FROM orders", "duration_ms": 500},
        ]
        
        for problem in test_cases:
            suggestion = analyzer.analyze_problem(problem)
            if suggestion:
                assert 0 <= suggestion.confidence <= 100, f"Confidence {suggestion.confidence} out of bounds"
    
    def test_code_example_validity(self, analyzer):
        """Test that code examples are non-empty strings"""
        problems = [
            {"type": "N+1", "sql": "SELECT * FROM books WHERE id = ?", "count": 5},
            {"type": "MISSING_INDEX", "sql": "SELECT * FROM users WHERE email = ?"},
        ]
        
        for problem in problems:
            suggestion = analyzer.analyze_problem(problem)
            if suggestion and suggestion.code_example:
                assert isinstance(suggestion.code_example, str)
                assert len(suggestion.code_example) > 0


class TestPerformanceAndStress:
    """Stress tests and performance benchmarks"""
    
    def test_analyze_1000_problems(self):
        """Test analyzing 1000 problems"""
        problems = [
            {"type": "N+1", "sql": f"SELECT * FROM t{i} WHERE id = ?", "count": i % 100}
            for i in range(1000)
        ]
        
        insights = AIAnalyzer.generate_insights(problems)
        assert insights["problems_analyzed"] == 1000
    
    def test_mixed_problem_types_100(self):
        """Test with 100 mixed problem types"""
        types = ["N+1", "MISSING_INDEX", "SLOW_QUERY", "SEQ_SCAN", "SEQUENTIAL_QUERIES", "TABLE_SCAN"]
        problems = [
            {"type": types[i % len(types)], "sql": f"SELECT * FROM t{i}", "count": i, "duration_ms": i * 10}
            for i in range(100)
        ]
        
        insights = AIAnalyzer.generate_insights(problems)
        assert insights["problems_analyzed"] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
