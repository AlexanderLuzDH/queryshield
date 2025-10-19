from collections import defaultdict
from typing import Any, Dict, List, Tuple

from .capture import QueryEvent
from .utils import normalize_sql


def classify_n_plus_one(
    events: List[QueryEvent], threshold: int = 5
) -> Tuple[List[Dict[str, Any]], Dict[int, str]]:
    """Detect naive N+1 by repeating normalized SQL at same top stack.

    Returns: (problems, event_tags) where event_tags maps event index to a tag id.
    """
    clusters: Dict[Tuple[str, Tuple[str, str, int]], List[int]] = defaultdict(list)
    normalized: List[str] = [normalize_sql(e.sql) for e in events]
    for idx, e in enumerate(events):
        top = e.stack[0] if e.stack else ("<unknown>", "?", 0)
        key = (normalized[idx], top)
        clusters[key].append(idx)

    problems: List[Dict[str, Any]] = []
    event_tags: Dict[int, str] = {}
    tag_counter = 1

    for (norm_sql, top), idxs in clusters.items():
        if len(idxs) >= threshold:
            tag = f"n+1_cluster_{tag_counter}"
            tag_counter += 1
            for i in idxs:
                event_tags[i] = tag
            sample = events[idxs[0]]
            top_file, top_func, top_line = sample.stack[0] if sample.stack else ("<unknown>", "?", 0)
            problem_id = f"n+1:{top_file}:{top_line}"
            # basic heuristic: if normalized SQL references a *_id column, prefer select_related
            suggestion_kind = "select_related" if ("_id = ?" in norm_sql or "_id = $" in norm_sql) else "prefetch_related"
            problems.append(
                {
                    "id": problem_id,
                    "type": "N+1",
                    "evidence": {
                        "cluster_count": len(idxs),
                        "example_sql": norm_sql[:200],
                        "top_stack": [top_file, top_func, top_line],
                    },
                    "suggestion": {
                        "kind": suggestion_kind,
                        "args": [],
                    },
                    "explain": None,
                    "db_alias": getattr(sample, "db_alias", "default"),
                }
            )

    return problems, event_tags


def classify_all(events: List[QueryEvent], nplus1_threshold: int = 5) -> Tuple[List[Dict[str, Any]], Dict[int, List[str]]]:
    probs, tag_map = classify_n_plus_one(events, threshold=nplus1_threshold)
    tags: Dict[int, List[str]] = defaultdict(list)
    for idx, tag in tag_map.items():
        tags[idx].append(tag)
    return probs, tags
