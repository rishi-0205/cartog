/** GraphQL resolver map. */
export const resolvers = { Query: { user(): void { return; } } };
export function resolveUser(): void { resolvers.Query.user(); }
