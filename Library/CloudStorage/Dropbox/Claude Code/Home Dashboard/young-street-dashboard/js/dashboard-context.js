const _ctx = {};
export function setContext(key, value) { _ctx[key] = value; }
export function getContext() { return { ..._ctx }; }
