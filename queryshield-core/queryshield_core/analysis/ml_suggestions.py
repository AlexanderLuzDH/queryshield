"""AI-powered root cause analysis and fix suggestions

Rule-based heuristics for common query performance patterns.
(Foundation for future ML enhancements)
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import re


@dataclass
class Suggestion:
    """Fix suggestion with confidence score"""
    
    root_cause: str  # What's actually wrong
    suggestion: str  # How to fix it
    code_example: Optional[str] = None  # Code snippet showing fix
    confidence: int = 50  # 0-100 confidence score
    estimated_improvement: str = ""  # "50x faster"
    similar_patterns: int = 0  # How many tests have this pattern


class AIAnalyzer:
    """Rule-based analyzer for query problems"""
    
    # Rule thresholds
    NPLUS1_MIN_COUNT = 5  # Flag N+1 if 5+ repeated queries
    SLOW_QUERY_MS = 500  # Flag slow queries >500ms
    SEQUENTIAL_QUERIES_MIN = 3  # 3+ sequential queries is suspicious
    
    def __init__(self):
        """Initialize analyzer with rules"""
        self.patterns = []
        self._register_rules()
    
    def _register_rules(self):
        """Register all analysis rules"""
        self.patterns = [
            self._check_nplus1,
            self._check_missing_index,
            self._check_slow_query,
            self._check_seq_scan,
            self._check_sort_without_index,
            self._check_sequential_queries,
            self._check_table_scan,
            self._check_join_order,
        ]
    
    def analyze_problem(self, problem: Dict[str, Any]) -> Optional[Suggestion]:
        """Analyze a single problem and generate suggestion
        
        Args:
            problem: Problem dict from report (type, sql, count, etc)
        
        Returns:
            Suggestion object or None if no analysis found
        """
        
        if not problem or not isinstance(problem, dict):
            return None
        
        problem_type = problem.get("type", "").upper()
        
        # Some problem types don't require SQL (e.g., SEQUENTIAL_QUERIES)
        sql_raw = problem.get("sql", "")
        if sql_raw and not isinstance(sql_raw, str):
            return None
        
        # Check each rule (rules will validate their own requirements)
        for rule_func in self.patterns:
            suggestion = rule_func(problem)
            if suggestion:
                return suggestion
        
        return None
    
    def _get_safe_sql(self, problem: Dict[str, Any]) -> str:
        """Safely get uppercase SQL from problem, returning empty string if None"""
        sql = problem.get("sql", "")
        if sql is None or not isinstance(sql, str):
            return ""
        return sql.upper()
    
    def _check_nplus1(self, problem: Dict[str, Any]) -> Optional[Suggestion]:
        """Detect N+1 query patterns"""
        
        if problem.get("type") != "N+1":
            return None
        
        sql = self._get_safe_sql(problem)
        if not sql:
            return None
        
        count = problem.get("count", 0)
        # Avoid division by zero
        count = max(1, count)
        
        # Pattern 1: Loop accessing foreign key
        if "WHERE ID =" in sql or "WHERE ID IN" in sql:
            return Suggestion(
                root_cause="Loop iterates collection, accesses foreign key without prefetch",
                suggestion="Use ORM lazy loading optimization: joinedload(), select_related(), or prefetch_related()",
                code_example="""# Django
from django.db.models import Prefetch
books = Book.objects.select_related('author').all()

# SQLAlchemy
from sqlalchemy.orm import joinedload
books = db.query(Book).options(joinedload(Book.author)).all()""",
                confidence=95,
                estimated_improvement=f"{count}x faster ({count}ms → {max(1, count//count)}ms)",
                similar_patterns=count,
            )
        
        # Pattern 2: Accessing collection
        if "COUNT(*)" in sql or "SELECT COUNT" in sql:
            return Suggestion(
                root_cause="Counting related items in loop (e.g., author.books.count())",
                suggestion="Use annotated count or eager-load with Count aggregate",
                code_example="""# Django
from django.db.models import Count, Prefetch
authors = Author.objects.annotate(book_count=Count('books'))

# SQLAlchemy
from sqlalchemy import func
stmt = select(Author, func.count(Book.id).label('book_count'))
    .outerjoin(Book)
    .group_by(Author.id)""",
                confidence=80,
                estimated_improvement=f"{count}x faster",
                similar_patterns=count,
            )
        
        return None
    
    def _check_missing_index(self, problem: Dict[str, Any]) -> Optional[Suggestion]:
        """Detect missing index patterns from EXPLAIN"""
        
        if problem.get("type") != "MISSING_INDEX":
            return None
        
        sql = self._get_safe_sql(problem)
        explain_output = problem.get("explain", "")
        
        # Try to extract column from WHERE clause first
        where_match = re.search(r"WHERE\s+(\w+)\s*=", sql)
        if where_match:
            column = where_match.group(1).lower()
            
            return Suggestion(
                root_cause=f"Column '{column}' used in WHERE clause without index",
                suggestion=f"Add index: CREATE INDEX idx_{column} ON table({column})",
                code_example=f"CREATE INDEX idx_{column} ON table({column});",
                confidence=90,
                estimated_improvement="10-100x faster",
                similar_patterns=1,
            )
        
        # Try to extract from JOIN condition
        join_match = re.search(r"JOIN\s+\w+\s+\w+\s+ON\s+\w+\.(\w+)\s*=", sql)
        if join_match:
            column = join_match.group(1).lower()
            
            return Suggestion(
                root_cause=f"Column '{column}' used in JOIN condition without index",
                suggestion=f"Add index: CREATE INDEX idx_{column} ON table({column})",
                code_example=f"CREATE INDEX idx_{column} ON table({column});",
                confidence=85,
                estimated_improvement="10-100x faster",
                similar_patterns=1,
            )
        
        return None
    
    def _check_slow_query(self, problem: Dict[str, Any]) -> Optional[Suggestion]:
        """Detect slow queries"""
        
        if problem.get("type") != "SLOW_QUERY":
            return None
        
        duration = problem.get("duration_ms", 0)
        sql = self._get_safe_sql(problem)
        
        # Pattern 1: Complex JOIN (check this FIRST before SELECT *)
        if sql.count("JOIN") >= 3:
            join_count = sql.count("JOIN")
            return Suggestion(
                root_cause=f"{join_count} JOINs in query - complex multi-table join",
                suggestion="Consider breaking into multiple queries or optimizing JOIN order",
                code_example="# Use query profiler to find bottleneck JOIN",
                confidence=65,
                estimated_improvement="30% faster",
                similar_patterns=1,
            )
        
        # Pattern 2: Full table scan
        if "SELECT *" in sql:
            return Suggestion(
                root_cause=f"SELECT * taking {duration}ms - likely selecting unnecessary columns",
                suggestion="Select only needed columns to reduce I/O",
                code_example="""# Bad
SELECT * FROM users;

# Good
SELECT id, email, name FROM users;""",
                confidence=70,
                estimated_improvement="20-50% faster",
                similar_patterns=1,
            )
        
        return None
    
    def _check_seq_scan(self, problem: Dict[str, Any]) -> Optional[Suggestion]:
        """Detect sequential scans in EXPLAIN"""
        
        explain = problem.get("explain_plan", {})
        if not explain or "Seq Scan" not in str(explain):
            return None
        
        # Find table name from EXPLAIN
        plan_str = str(explain)
        table_match = re.search(r"Seq Scan on (\w+)", plan_str)
        table = table_match.group(1) if table_match else "table"
        
        return Suggestion(
            root_cause=f"Sequential scan on {table} - reading entire table instead of using index",
            suggestion="Add index on WHERE clause columns or JOIN conditions",
            code_example=f"CREATE INDEX idx_{table}_lookup ON {table}(id);",
            confidence=85,
            estimated_improvement="50-1000x faster",
            similar_patterns=1,
        )
    
    def _check_sort_without_index(self, problem: Dict[str, Any]) -> Optional[Suggestion]:
        """Detect sorts without index"""
        
        if problem.get("type") != "SORT":
            return None
        
        explain = problem.get("explain_plan", {})
        sql = self._get_safe_sql(problem)
        
        if not ("Sort" in str(explain) and "ORDER BY" in sql):
            return None
        
        # Extract ORDER BY columns
        order_match = re.search(r"ORDER BY\s+([\w\s,\.]+)", sql)
        if order_match:
            columns = order_match.group(1).lower()
            
            return Suggestion(
                root_cause=f"Expensive in-memory sort on {columns} without index",
                suggestion=f"Create index: CREATE INDEX idx_order ON table({columns})",
                code_example=f"CREATE INDEX idx_order ON table({columns});",
                confidence=88,
                estimated_improvement="10-100x faster",
                similar_patterns=1,
            )
        
        return None
    
    def _check_sequential_queries(self, problem: Dict[str, Any]) -> Optional[Suggestion]:
        """Detect sequential queries (waterfall pattern)"""
        
        if problem.get("type") != "SEQUENTIAL_QUERIES":
            return None
        
        count = problem.get("count", 0)
        if count < self.SEQUENTIAL_QUERIES_MIN:
            return None
        
        return Suggestion(
            root_cause=f"{count} sequential queries executed one after another",
            suggestion="Batch queries together or use a single JOIN query",
            code_example="""# Bad: Sequential queries
result1 = get_users()  # Query 1
for user in result1:
    result2 = get_orders(user.id)  # Query 2 per user

# Good: Batch query
result = get_users_with_orders()  # 1-2 queries""",
            confidence=75,
            estimated_improvement=f"{count}x faster",
            similar_patterns=count,
        )
    
    def _check_table_scan(self, problem: Dict[str, Any]) -> Optional[Suggestion]:
        """Detect full table scans"""
        
        sql = self._get_safe_sql(problem)
        if "SELECT" not in sql or "WHERE" not in sql:
            return None
        
        # If WHERE but potentially unindexed
        if re.search(r"WHERE\s+\w+\s*LIKE", sql):
            return Suggestion(
                root_cause="LIKE query without full-text index",
                suggestion="Consider using full-text search index for LIKE queries",
                code_example="""# PostgreSQL
CREATE INDEX idx_text_search ON users USING GIN(to_tsvector('english', name));

# MySQL
ALTER TABLE users ADD FULLTEXT idx_name (name);""",
                confidence=70,
                estimated_improvement="100x faster",
                similar_patterns=1,
            )
        
        return None
    
    def _check_join_order(self, problem: Dict[str, Any]) -> Optional[Suggestion]:
        """Detect poor JOIN order"""
        
        # Handle explicit JOIN_ORDER problem type
        if problem.get("type") == "JOIN_ORDER":
            sql = self._get_safe_sql(problem)
            explain = problem.get("explain_plan", {})
            join_count = sql.count("JOIN")
            
            return Suggestion(
                root_cause=f"JOIN order issue: Poor join order with {join_count} tables - possible nested loop",
                suggestion="Reorder JOINs from most restrictive to least restrictive",
                code_example="""# Bad: Start with large table
SELECT * FROM orders o
  JOIN users u ON o.user_id = u.id
  JOIN products p ON o.product_id = p.id;

# Good: Start with most filtered table
SELECT * FROM users u
  JOIN orders o ON u.id = o.user_id
  JOIN products p ON o.product_id = p.id
  WHERE u.status = 'active';""",
                confidence=72,
                estimated_improvement="20-50% faster",
                similar_patterns=1,
            )
        
        # Check for implicit JOIN_ORDER issues from EXPLAIN
        explain = problem.get("explain_plan", {})
        sql = self._get_safe_sql(problem)
        
        join_count = sql.count("JOIN")
        if join_count < 2:
            return None
        
        explain_str = str(explain)
        # Check for cross join or cartesian product indicators
        if "cross join" in explain_str.lower() or "Nested Loop" in explain_str:
            return Suggestion(
                root_cause=f"Poor join order with {join_count} tables - possible nested loop",
                suggestion="Reorder JOINs from most restrictive to least restrictive",
                code_example="""# Bad: Start with large table
SELECT * FROM orders o
  JOIN users u ON o.user_id = u.id
  JOIN products p ON o.product_id = p.id;

# Good: Start with most filtered table
SELECT * FROM users u
  JOIN orders o ON u.id = o.user_id
  JOIN products p ON o.product_id = p.id
  WHERE u.status = 'active';""",
                confidence=72,
                estimated_improvement="20-50% faster",
                similar_patterns=1,
            )
        
        return None
    
    @staticmethod
    def generate_insights(problems: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate insights from all problems
        
        Args:
            problems: List of problem dicts from report
        
        Returns:
            Dict with insights and suggestions
        """
        
        analyzer = AIAnalyzer()
        insights = {
            "problems_analyzed": len(problems),
            "suggestions": [],
            "hotspots": [],
            "optimization_potential": 0,
            "confidence_score": 0,
        }
        
        # Analyze each problem
        confidence_scores = []
        for problem in problems:
            suggestion = analyzer.analyze_problem(problem)
            if suggestion:
                insights["suggestions"].append({
                    "type": problem.get("type"),
                    "root_cause": suggestion.root_cause,
                    "suggestion": suggestion.suggestion,
                    "code_example": suggestion.code_example,
                    "confidence": suggestion.confidence,
                    "estimated_improvement": suggestion.estimated_improvement,
                })
                confidence_scores.append(suggestion.confidence)
                
                # Track hotspots
                if suggestion.similar_patterns > 5:
                    insights["hotspots"].append({
                        "type": problem.get("type"),
                        "frequency": suggestion.similar_patterns,
                        "severity": "HIGH" if suggestion.confidence > 80 else "MEDIUM",
                    })
        
        # Calculate average confidence
        if confidence_scores:
            insights["confidence_score"] = int(sum(confidence_scores) / len(confidence_scores))
        
        # Estimate optimization potential
        high_confidence = len([s for s in insights["suggestions"] if s["confidence"] > 80])
        insights["optimization_potential"] = min(100, high_confidence * 25)
        
        return insights
