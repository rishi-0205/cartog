/** Object-literal service container reached through wildcard barrel. */
export const svc = {
  handle(data: unknown): unknown { return validateData(data); },
};
function validateData(d: unknown): unknown { return d; }
