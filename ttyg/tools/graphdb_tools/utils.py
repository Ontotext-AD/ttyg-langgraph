import re


def to_sparql_literal(query: str) -> str:
    escaped_query = re.sub(r"([\W_])", r"\\\1", query)
    sparql_literal = escaped_query.replace("\\", "\\\\").replace("'", "\\'")
    return f"'''{sparql_literal}'''"
