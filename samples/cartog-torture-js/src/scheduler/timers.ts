/** setTimeout/setInterval — timer and TTL spines. */
import { cacheExpire } from "../utils/cache.util.js";
setTimeout(() => cacheExpire("k", 1), 0);
setInterval(() => cacheExpire("k", 60), 1000);
