// PATTERN: CALL-ARROW-01 — arrow function assigned to const
const parse = () => { return; };
// PATTERN: CALL-BIND-01 — .bind()/.call()/.apply()
const bound = parse.bind(null);
bound.call(null);
bound.apply(null);
