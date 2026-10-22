def to_sparql_literal(query: str) -> str:
    escaped = query.replace("\\", "\\\\")
    escaped = escaped.replace("'", "\\'")
    return f"'''{escaped}'''"
