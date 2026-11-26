// Renders templates/page.html's script against a stub DOM and a folder that stands for the
// learner's store, and prints what happened as JSON:
//   {text: <all rendered text and HTML>, ids: {<element id>: <its text/HTML>}, styles, hidden,
//    fetched: [<every path the page asked for>], saved: [<downloads the page made>]}
//    db: [<every document the page wrote to its database, as {path, data}>],
//    storage: <the browser storage (localStorage) as the page left it, or null without one>}
// Usage: node page_harness.js <page.html> <store folder> [--downloads] [--db [file]] [--storage file | --no-storage] [--set id=text,…] [--click id,id,…]
// --downloads: the page is given the downloads capability (its Export button);
// --db: the page is given its database (where it keeps cme/prefs); with a JSON file, that is
//   the cme/prefs document it finds there;
// --storage: the JSON file holds what the browser storage has when the page loads ({key: text});
//   --no-storage: the browser refuses storage (every use throws);
// --click: after the page has loaded, click these elements in turn (an element the page made
//   and gave an id counts);
// --set: before a click on an element <name>-save, the input <name>-input is given this text
//   (--set lvl=…), as if the learner had typed it. The text is URI-encoded.
const fs = require("fs");
const path = require("path");
const [pagePath, storeDir, ...opts] = process.argv.slice(2);
const html = fs.readFileSync(pagePath, "utf8");
const scripts = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const withDownloads = opts.includes("--downloads");
const optValue = (name) => opts.includes(name) ? (opts[opts.indexOf(name) + 1] || "") : "";
const clicks = optValue("--click").split(",").filter(Boolean);
const typed = Object.fromEntries(optValue("--set").split(",").filter(Boolean).map(x => [x.split("=")[0], decodeURIComponent(x.split("=").slice(1).join("="))]));
const withDb = opts.includes("--db");
const dbFile = withDb && optValue("--db") && !optValue("--db").startsWith("--") ? optValue("--db") : null;
let dbDoc = dbFile ? JSON.parse(fs.readFileSync(dbFile, "utf8")) : null;
const dbWrites = [];
const db = {doc: (p) => ({
  get: async () => ({exists: dbDoc != null, data: () => dbDoc}),
  set: async (data) => { dbDoc = JSON.parse(JSON.stringify(data)); dbWrites.push({path: p, data: dbDoc}); },
})};

// elements the markup hides from the start (<… id="x" … hidden>)
const hiddenAtStart = new Set([...html.matchAll(/<[a-z][^>]*\bid="([^"]+)"[^>]*>/g)].filter(m => /\shidden[\s>=]/.test(m[0])).map(m => m[1]));
const all = [];
function el(id) {
  const store = {id: id || "", textContent: "", innerHTML: "", children: [], hidden: hiddenAtStart.has(id), dataset: {}, style: {}, value: "", _on: {}};
  all.push(store);
  const noop = () => undefined;
  return new Proxy(store, {
    get(t, k) {
      if (k in t) return t[k];
      if (k === "appendChild" || k === "insertBefore") return (c) => { t.children.push(c); return c; };
      if (k === "addEventListener") return (ev, fn) => { (t._on[ev] = t._on[ev] || []).push(fn); };
      if (k === "querySelector" || k === "closest") return () => el();
      if (k === "querySelectorAll") return () => [];
      if (k === "classList") return {add: noop, remove: noop, toggle: () => false, contains: () => false};
      if (k === "getAttribute") return () => null;
      if (typeof k === "symbol") return undefined;
      return noop;
    },
    set(t, k, v, proxy) { t[k] = v; if (k === "id" && v) byId[v] = proxy; return true; },
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
const fetched = [], saved = [];
const fetch = async (url) => {
  const rel = decodeURIComponent(String(url).split("?")[0]);
  fetched.push(rel);
  const file = path.join(storeDir, ...rel.split("/"));
  if (!rel.startsWith("data/") || rel.includes("..") || !fs.existsSync(file))
    return {ok: false, status: 404, json: async () => { throw new Error("404"); }, text: async () => ""};
  const body = fs.readFileSync(file, "utf8");
  return {ok: true, status: 200, json: async () => JSON.parse(body), text: async () => body};
};
const claude = (withDownloads || withDb) ? {use: async (what) =>
  what === "downloads" && withDownloads ? {save: async (x) => { saved.push(x); }} : what === "db" && withDb ? db : null} : undefined;
const stored = opts.includes("--storage") ? JSON.parse(fs.readFileSync(optValue("--storage"), "utf8")) : {};
const refuse = () => { throw new Error("storage is not available"); };
const localStorage = opts.includes("--no-storage") ? {getItem: refuse, setItem: refuse, removeItem: refuse}
  : {getItem: (k) => k in stored ? stored[k] : null, setItem: (k, v) => { stored[k] = String(v); }, removeItem: (k) => { delete stored[k]; }};
const window = {document, fetch, claude, localStorage, addEventListener: () => undefined, matchMedia: () => ({matches: false, addEventListener: () => undefined})};
const location = {hash: ""};
const requestAnimationFrame = (f) => f();
const run = new Function("window", "document", "fetch", "location", "requestAnimationFrame", "history", "navigator", "claude",
  scripts.join("\n;\n"));
run(window, document, fetch, location, requestAnimationFrame, {replaceState: () => undefined}, {}, claude);

const wait = (ms) => new Promise((res) => setTimeout(res, ms));
(async () => {
  await wait(200);
  const loaded = fetched.slice();
  for (const id of clicks) {
    const name = id.replace(/-save$/, "");
    if (id.endsWith("-save") && name in typed) document.getElementById(name + "-input").value = typed[name];
    for (const fn of ((byId[id] || {})._on || {}).click || []) await fn({});
    await wait(50);
  }
  const ids = {}, styles = {}, hidden = {};
  for (const [id, e] of Object.entries(byId)) {
    ids[id] = String(e.textContent || "") + String(e.innerHTML || "");
    hidden[id] = !!e.hidden;
    if (Object.keys(e.style).length) styles[id] = e.style;
  }
  const text = all.map(e => String(e.textContent || "") + "\n" + String(e.innerHTML || "")).join("\n");
  process.stdout.write(JSON.stringify({text, ids, styles, hidden, fetched, fetched_on_load: loaded, saved, db: dbWrites,
    storage: opts.includes("--no-storage") ? null : stored}));
  process.exit(0);
})();
