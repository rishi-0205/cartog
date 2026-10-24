// Pre-load hook for Node on Windows to safely escape single backslash in RegExp
const origRegExp = RegExp;

function SafeRegExp(pattern, flags) {
  if (pattern === '\\') {
    pattern = '[\\\\/]';
  }
  if (new.target) {
    return new origRegExp(pattern, flags);
  }
  return origRegExp(pattern, flags);
}

SafeRegExp.prototype = origRegExp.prototype;
Object.setPrototypeOf(SafeRegExp, origRegExp);
global.RegExp = SafeRegExp;
