"""GraphQL resolver map. PATTERN: RPC-GRAPHQL-01."""
resolvers = {"Query": {"user": lambda: None}}

def resolve_user():
    """Resolve the user query."""
    return resolvers["Query"]["user"]()
