"""EXPLAIN plan analysis and classification"""


def explain_classify(explain_plan):
    """
    Analyze EXPLAIN plan and classify query performance issues.
    
    Args:
        explain_plan: Dict containing EXPLAIN plan output
        
    Returns:
        List of classified issues with their severity
    """
    if not explain_plan:
        return []
    
    issues = []
    
    # Check for sequential scans
    if _has_seq_scan(explain_plan):
        issues.append({
            "type": "SEQ_SCAN",
            "severity": "HIGH",
            "recommendation": "Add index on frequently scanned columns"
        })
    
    # Check for expensive sorts
    if _has_expensive_sort(explain_plan):
        issues.append({
            "type": "EXPENSIVE_SORT",
            "severity": "MEDIUM",
            "recommendation": "Add composite index with sort column"
        })
    
    return issues


def _has_seq_scan(explain_plan):
    """Check if plan contains sequential scan nodes"""
    if not explain_plan or "Plan" not in explain_plan:
        return False
    
    return _search_plan_node(explain_plan["Plan"], "Seq Scan")


def _has_expensive_sort(explain_plan):
    """Check if plan contains expensive sort operations"""
    if not explain_plan or "Plan" not in explain_plan:
        return False
    
    return _search_plan_node(explain_plan["Plan"], "Sort")


def _search_plan_node(node, node_type):
    """Recursively search for node type in EXPLAIN plan"""
    if not node:
        return False
    
    if node.get("Node Type") == node_type:
        return True
    
    # Check nested plans
    if "Plans" in node:
        for subplan in node["Plans"]:
            if _search_plan_node(subplan, node_type):
                return True
    
    return False
