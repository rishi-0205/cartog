// PATTERN: MIDDLEWARE-ERROR-02 — error middleware form
app.use((err: unknown, req: unknown, res: unknown, next: unknown) => next(err));
declare const app: { use(f: unknown): void };
