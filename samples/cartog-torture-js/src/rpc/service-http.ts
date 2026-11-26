/** Inter-service REST call. */
export async function fetchService(path: string): Promise<unknown> { return fetch(`http://svc${path}`); }
