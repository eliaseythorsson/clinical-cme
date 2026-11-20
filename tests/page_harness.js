// Renders templates/page.html's script against a stub DOM and prints everything it put on the
// page as JSON: {text: <all rendered text and HTML>, ids: {<element id>: <its text/HTML>}}.
// Usage: node page_harness.js <page.html> <state.json>
const fs = require("fs");
const [pagePath, statePath] = process.argv.slice(2);
const html = fs.readFileSync(pagePath, "utf8");
const scripts = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const state = JSON.parse(fs.readFileSync(statePath, "utf8"));

const all = [];
function el(id) {
  const store = {id: id || "", textContent: "", innerHTML: "", children: [], hidden: false, dataset: {}, style: {}, value: ""};
  all.push(store);
  const noop = () => undefined;
  return new Proxy(store, {
    get(t, k) {
      if (k in t) return t[k];
      if (k === "appendChild" || k === "insertBefore") return (c) => { t.children.push(c); return c; };
      if (k === "querySelector" || k === "closest") return () => el();
      if (k === "querySelectorAll") return () => [];
      if (k === "classList") return {add: noop, remove: noop, toggle: () => false, contains: () => false};
      if (k === "getAttribute") return () => null;
      if (typeof k === "symbol") return undefined;
      return noop;
    },
    set(t, k, v) { t[k] = v; return true; },
  });
}
const byId = {};
const document = {
  getElementById: (id) => byId[id] || (byId[id] = el(id)),
  createElement: () => el(),
  querySelector: () => el(),
  querySelectorAll: () => [],
  addEventListener: () => undefined,
};
const fetch = async (url) => {
  if (String(url).includes("data/state.json")) return {ok: true, status: 200, json: async () => state, text: async () => JSON.stringify(state)};
  return {ok: false, status: 404, json: async () => { throw new Error("404"); }, text: async () => ""};
};
const window = {document, fetch, addEventListener: () => undefined, matchMedia: () => ({matches: false, addEventListener: () => undefined})};
const location = {hash: ""};
const requestAnimationFrame = (f) => f();
const run = new Function("window", "document", "fetch", "location", "requestAnimationFrame", "history", "navigator",
  scripts.join("\n;\n"));
run(window, document, fetch, location, requestAnimationFrame, {replaceState: () => undefined}, {});

setTimeout(() => {
  const ids = {};
  for (const [id, e] of Object.entries(byId)) ids[id] = String(e.textContent || "") + String(e.innerHTML || "");
  const text = all.map(e => String(e.textContent || "") + "\n" + String(e.innerHTML || "")).join("\n");
  process.stdout.write(JSON.stringify({text, ids}));
  process.exit(0);
}, 200);
