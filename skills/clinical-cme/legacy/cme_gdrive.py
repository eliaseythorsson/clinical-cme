#!/usr/bin/env python3
"""
cme_gdrive.py - Google Drive home for the clinical-cme skill (version 3.2).

Standard library only; runs on Python 3.8+. Used together with cme_ledger.py when the
learner's CME files live in Google Drive rather than in a folder on their computer.

The Google connectors carry file contents inside each tool call, so this helper keeps every
write small and every read exact:

  * The ledger is kept as an append-only JOURNAL: one checksummed line per change, in a
    Google Doc. `journal-replay` rebuilds the ledger from the journal; `journal-make` applies
    a change to the working ledger and prints the line(s) and the Docs request that appends
    them at the end of the doc (no read is needed before the write).
  * Version 3.2 speed rules: reads are plain-text exports (download_file_content), which the
    connector saves to a file; an inline read is never copied by hand (pass --revision and
    --end-index instead); the blueprint is cached in the ledger; the index doc's end position
    is remembered between sessions; part A of a session doc is written in one pass.
  * Each session is its own Google Doc in the Sessions folder, created from HTML
    (`gdoc-html`) and completed with styled paragraphs (`gdoc-append`). An index doc lists
    every session.
  * Google Doc reads (read_doc JSON, a text export, or plain text) are parsed by `gdoc-text`.

Commands
  journal-make     apply one change to a working ledger and print the journal line + request
  journal-replay   rebuild the ledger from one or more journal volumes (verifies checksums)
  gdoc-text        exact plain text (plus revision and end index) of a saved Docs read
  gdoc-html        Markdown -> compact HTML for creating a formatted Google Doc
  gdoc-frame       the header and pending-marker HTML of a session doc (part A in one pass)
  gdoc-append      update_doc requests that append (or replace the pending marker with)
                   Markdown text as styled paragraphs
  gdoc-insert      update_doc requests that insert exact plain text (journal header,
                   blueprint, resource library) at the end of a doc
  gdoc-verify      check that a doc ends with the expected text and has no pending marker
  gdoc-period      list the session docs of a review period (or all), from the ledger
  gdoc-backfill    HTML and index lines for sessions recorded before version 3
"""

import argparse
import base64
import contextlib
import copy
import datetime as dt
import hashlib
import html
import io
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cme_ledger as L  # noqa: E402

JOURNAL_TAG = "CMEJ"
JOURNAL_VERSION = "v1"
JOURNAL_HEADER = ("CME ledger journal — the machine record of your clinical-cme ledger. "
                  "The skill adds one line per change. Please do not edit this document.")
PENDING_TAG = "CME-PENDING"
ROLLOVER_CHARS = 900000          # Google Docs hold at most ~1.02 million characters
EVENT_TYPES = ("init", "import", "migrate", "record", "review", "settings", "snooze",
               "mark-unrecorded", "backfill", "home", "logdoc-open", "logdoc-update",
               "resolve-conflict", "blueprint-cache", "doc-state")
LOGDOC_KEYS = ("doc_id", "url", "title", "summary", "tags", "date", "indexed")


def die(msg, code=2):
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(code)


def utf16len(s):
    return len(s.encode("utf-16-le")) // 2


def digest(ledger):
    text = json.dumps(ledger, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_file(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def write_file(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


# ------------------------------------------------------------------ Google Doc reads

def _find_document(obj, depth=0):
    """Find a documents.get object inside whatever wrapper the connector result used."""
    if depth > 8:
        return None
    if isinstance(obj, dict):
        if "revisionId" in obj and ("body" in obj or "tabs" in obj):
            return obj
        for v in obj.values():
            hit = _find_document(v, depth + 1)
            if hit:
                return hit
    elif isinstance(obj, list):
        for v in obj:
            hit = _find_document(v, depth + 1)
            if hit:
                return hit
    elif isinstance(obj, str):
        t = obj.strip()
        if t[:1] in "{[":
            try:
                return _find_document(json.loads(t), depth + 1)
            except json.JSONDecodeError:
                return None
    return None


def _find_base64(obj, depth=0):
    if depth > 6:
        return None
    if isinstance(obj, dict):
        for k in ("content", "data", "fileContent", "base64", "text", "body"):
            if isinstance(obj.get(k), str) and _looks_base64(obj[k]):
                return obj[k]
        for v in obj.values():
            hit = _find_base64(v, depth + 1)
            if hit:
                return hit
    elif isinstance(obj, list):
        for v in obj:
            hit = _find_base64(v, depth + 1)
            if hit:
                return hit
    elif isinstance(obj, str) and _looks_base64(obj):
        return obj
    return None


def _looks_base64(s):
    s = s.strip()
    return len(s) >= 16 and len(s) % 4 == 0 and re.fullmatch(r"[A-Za-z0-9+/=\s]+", s[:5000]) is not None


def _paragraph_text(par, as_markdown):
    text = "".join((el.get("textRun") or {}).get("content", "") for el in par.get("elements") or [])
    if as_markdown:
        style = (par.get("paragraphStyle") or {}).get("namedStyleType") or ""
        body = text.rstrip("\n")
        m = re.match(r"HEADING_(\d)", style)
        if m and not body.lstrip().startswith("#"):
            text = "#" * int(m.group(1)) + " " + text
        elif par.get("bullet") and not re.match(r"^\s*[-*]\s", body):
            text = "- " + text
    return text


def parse_document(doc, as_markdown=False):
    tabs = doc.get("tabs")
    if tabs:
        body = ((tabs[0].get("documentTab") or {}).get("body")) or {}
    else:
        body = doc.get("body") or {}
    content = body.get("content") or []
    paragraphs, chunks = [], []
    for el in content:
        if "paragraph" in el:
            t = _paragraph_text(el["paragraph"], as_markdown)
            paragraphs.append({"start": el.get("startIndex", 0), "end": el.get("endIndex", 0),
                               "text": t,
                               "style": (el["paragraph"].get("paragraphStyle") or {}).get("namedStyleType")})
            chunks.append(t)
        elif "table" in el:
            for row in el["table"].get("tableRows") or []:
                cells = []
                for cell in row.get("tableCells") or []:
                    cells.append("".join(_paragraph_text(c["paragraph"], False).replace("\n", " ")
                                         for c in cell.get("content") or [] if "paragraph" in c).strip())
                chunks.append("| " + " | ".join(cells) + " |\n")
    end_index = max([el.get("endIndex", 0) for el in content] + [1])
    return {"revision": doc.get("revisionId"), "doc_id": doc.get("documentId"),
            "title": doc.get("title"), "end_index": end_index,
            "text": "".join(chunks), "paragraphs": paragraphs}


def load_gdoc(path, as_markdown=False):
    """Return {"kind", "text", "revision", "end_index", "doc_id", "title", "paragraphs"}."""
    raw = read_file(path)
    obj = None
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        obj = None
    if obj is not None:
        doc = _find_document(obj)
        if doc:
            out = parse_document(doc, as_markdown)
            out["kind"] = "read_doc"
            return out
        b64 = _find_base64(obj)
        if b64:
            return {"kind": "export", "text": base64.b64decode(b64).decode("utf-8-sig"),
                    "revision": None, "end_index": None, "doc_id": None, "title": None,
                    "paragraphs": None}
    stripped = raw.strip()
    if _looks_base64(stripped) and "\n" not in stripped[:200] and " " not in stripped[:200]:
        try:
            return {"kind": "export", "text": base64.b64decode(stripped).decode("utf-8-sig"),
                    "revision": None, "end_index": None, "doc_id": None, "title": None,
                    "paragraphs": None}
        except (ValueError, UnicodeDecodeError):
            pass
    return {"kind": "text", "text": raw, "revision": None, "end_index": None, "doc_id": None,
            "title": None, "paragraphs": None}


def cmd_gdoc_text(args):
    g = load_gdoc(args.doc, as_markdown=args.markdown)
    if g["kind"] == "export":
        g["text"] = g["text"].replace("\r\n", "\n")
    if args.out:
        write_file(args.out, g["text"])
    if args.cache_json:
        # payload for a blueprint-cache journal event (--also blueprint-cache:<this file>)
        write_file(args.cache_json, json.dumps({"text": g["text"], "modified": args.modified,
                                                "doc_id": args.doc_id or g["doc_id"]}, ensure_ascii=False))
    print(json.dumps({"ok": True, "kind": g["kind"], "doc_id": g["doc_id"], "title": g["title"],
                      "revision": g["revision"], "end_index": g["end_index"],
                      "chars": len(g["text"]), "out": args.out,
                      "pending_markers": re.findall(PENDING_TAG + r" (S\d{3,})", g["text"]),
                      "text": None if args.out else g["text"]}, indent=2, ensure_ascii=False))


# ------------------------------------------------------------------ journal

def event_line(seq, date, etype, payload):
    body = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    head = "%s|%s|%06d|%s|%s" % (JOURNAL_TAG, JOURNAL_VERSION, seq, date, etype)
    sha = hashlib.sha256((head + "|" + body).encode("ascii")).hexdigest()[:16]
    return "%s|%s|%s" % (head, sha, body)


_NON_ASCII = re.compile(r"[^\x00-\x7f]")


def ascii_escape(text):
    """Re-escape non-ASCII characters exactly as json.dumps(ensure_ascii=True) writes them."""
    return _NON_ASCII.sub(lambda m: json.dumps(m.group(0))[1:-1], text)


LINE_RE = re.compile(r"^%s\|(v\d+)\|(\d{6})\|(\d{4}-\d{2}-\d{2})\|([a-z\-]+)\|([0-9a-f]{16})\|(.*)$" % JOURNAL_TAG)


def parse_journal_text(text, source="journal"):
    events, errors, warnings = [], [], []
    for n, line in enumerate(text.splitlines(), 1):
        line = line.strip().strip("\u000b")
        if not line.startswith(JOURNAL_TAG + "|"):
            continue
        m = LINE_RE.match(line)
        if not m:
            errors.append("%s line %d: malformed journal line" % (source, n))
            continue
        ver, seq, date, etype, sha, body = m.groups()
        head = "%s|%s|%s|%s|%s" % (JOURNAL_TAG, ver, seq, date, etype)
        # The Google Docs connector turns \uXXXX escapes in inserted text into the characters
        # themselves; restore the escapes so the checksum covers the line as it was written.
        body = ascii_escape(body)
        if hashlib.sha256((head + "|" + body).encode("ascii", "replace")).hexdigest()[:16] != sha:
            errors.append("%s line %d (event %s): checksum mismatch — the line was changed" % (source, n, seq))
            continue
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            errors.append("%s line %d: payload is not JSON" % (source, n))
            continue
        if etype not in EVENT_TYPES:
            errors.append("%s line %d: unknown event type %s" % (source, n, etype))
            continue
        events.append({"seq": int(seq), "date": date, "type": etype, "sha": sha,
                       "payload": payload, "source": source, "line": n})
    return events, errors, warnings


def order_events(events):
    """Sort by seq; drop exact duplicates (a retried append); flag conflicts and gaps."""
    errors, warnings, out = [], [], []
    keep = {int(e["payload"].get("seq", -1)): e["payload"].get("keep_sha")
            for e in events if e["type"] == "resolve-conflict"}
    by_seq = {}
    for e in sorted(events, key=lambda e: e["seq"]):
        prev = by_seq.get(e["seq"])
        if prev and prev["sha"] != e["sha"] and keep.get(e["seq"]) in (prev["sha"], e["sha"]):
            winner = e if keep[e["seq"]] == e["sha"] else prev
            if winner is e:
                out[out.index(prev)] = e
                by_seq[e["seq"]] = e
            warnings.append("conflict at %06d resolved earlier: kept %s" % (e["seq"], keep[e["seq"]]))
            continue
        if prev:
            if prev["sha"] == e["sha"]:
                warnings.append("event %06d appears twice (a repeated write); the copy is ignored" % e["seq"])
            else:
                errors.append("two different events share number %06d (%s line %d and %s line %d): "
                              "two sessions wrote at the same time" % (e["seq"], prev["source"], prev["line"],
                                                                       e["source"], e["line"]))
            continue
        by_seq[e["seq"]] = e
        out.append(e)
    for i, e in enumerate(out):
        if e["seq"] != i + 1:
            errors.append("event numbers jump from %06d to %06d: a line is missing" % (i, e["seq"]))
            break
    return out, errors, warnings


class EventError(Exception):
    pass


def _run_cmd(fn, ns):
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            fn(ns)
    except SystemExit as exc:
        text = buf.getvalue().strip()
        if exc.code not in (0, None):
            try:
                msg = json.loads(text.splitlines()[-1]).get("error")
            except (json.JSONDecodeError, IndexError):
                msg = text
            raise EventError(msg or "command failed")
    text = buf.getvalue().strip()
    try:
        return json.loads(text) if text else {}
    except json.JSONDecodeError:
        return {"output": text}


def apply_event(ledger, etype, date, payload):
    """Apply one event to a ledger (dict or None). Returns (ledger, result)."""
    tmpdir = tempfile.mkdtemp(prefix="cmej-")
    lp = os.path.join(tmpdir, "ledger.json")
    pp = os.path.join(tmpdir, "payload.json")

    def ns(**kw):
        base = {"today": date, "out": None, "ledger": lp, "force": False}
        base.update(kw)
        return argparse.Namespace(**base)

    try:
        if etype == "init":
            if ledger is not None:
                raise EventError("init on a journal that already has a ledger")
            res = _run_cmd(L.cmd_init, ns(out=lp, profile=json.dumps(payload.get("profile") or {}),
                                          config=json.dumps(payload.get("config") or {}), force=True))
            ledger = L.load_json(lp)
        elif etype == "import":
            if ledger is not None and not payload.get("replace"):
                raise EventError("import on a journal that already has a ledger")
            ledger = copy.deepcopy(payload["ledger"])
            changes = []
            if ledger.get("schema_version", 1) < L.SCHEMA_VERSION:
                changes = L.migrate_in_memory(ledger, L.parse_date(date))
            res = {"ok": True, "imported_sessions": len(L.sessions(ledger)), "migrated": changes}
        else:
            if ledger is None:
                raise EventError("the journal must start with init or import")
            L.save_ledger(ledger, lp)
            if etype == "migrate":
                res = _run_cmd(L.cmd_migrate, ns())
            elif etype == "record":
                with open(pp, "w", encoding="utf-8") as fh:
                    json.dump(payload["round"], fh, ensure_ascii=False)
                res = _run_cmd(L.cmd_record, ns(round=pp))
                ledger = L.load_json(lp)
                # v3.2: the session doc is registered by the record event itself (no separate
                # logdoc-open round trip in the middle of the session)
                ld = payload.get("logdoc")
                if ld:
                    sid = ld.get("log_id") or res.get("log_id")
                    reg = gdocs(ledger)
                    if sid not in reg["sessions"]:
                        reg["sessions"][sid] = {k: ld.get(k) for k in LOGDOC_KEYS}
                        reg["sessions"][sid].update({"opened": date, "closed": False, "recorded": True})
                        meta = ledger.setdefault("log", {"file": L.LOG_FILENAME})
                        if L.id_num(sid) > L.id_num(meta.get("last_id")):
                            meta["last_id"] = sid
                    else:
                        reg["sessions"][sid].update({k: ld[k] for k in LOGDOC_KEYS if ld.get(k) is not None})
                if payload.get("index_state"):
                    _set_doc_state(ledger, "index", payload["index_state"])
                L.save_ledger(ledger, lp)
            elif etype == "review":
                with open(pp, "w", encoding="utf-8") as fh:
                    json.dump(payload["review"], fh, ensure_ascii=False)
                res = _run_cmd(L.cmd_review, ns(review=pp))
            elif etype == "settings":
                res = _run_cmd(L.cmd_settings, ns(config=json.dumps(payload["config"]) if payload.get("config") else None,
                                                  profile=json.dumps(payload["profile"]) if payload.get("profile") else None))
            elif etype == "snooze":
                res = _run_cmd(L.cmd_snooze, ns(days=int(payload.get("days", 7))))
            elif etype == "mark-unrecorded":
                res = _run_cmd(L.cmd_log_mark_unrecorded, ns(id=payload["id"]))
            ledger = L.load_json(lp) if etype in ("migrate", "record", "review", "settings", "snooze",
                                                  "mark-unrecorded") else ledger
            if etype == "backfill":
                ids = []
                for i, s in enumerate(L.sessions(ledger)):
                    if not s.get("log_id"):
                        s["log_id"] = "S%04d" % (i + 1)
                        ids.append(s["log_id"])
                meta = ledger.setdefault("log", {"file": L.LOG_FILENAME})
                meta["backfilled"] = True
                if ids:
                    meta["last_id"] = max([meta.get("last_id") or "S0000"] + ids, key=L.id_num)
                reg = gdocs(ledger)
                for sid in ids:
                    reg["sessions"][sid] = {"doc_id": payload.get("doc_id"), "url": payload.get("url"),
                                            "title": "Reconstructed session", "reconstructed": True,
                                            "opened": date, "closed": True, "recorded": True,
                                            "date": next((s.get("date") for s in L.sessions(ledger)
                                                          if s.get("log_id") == sid), None)}
                res = {"ok": True, "ids": ids}
            elif etype == "home":
                st = ledger.setdefault("config", {}).setdefault("storage", {})
                L.deep_merge(st, payload)
                res = {"ok": True, "storage": st}
            elif etype == "logdoc-open":
                sid = payload["log_id"]
                reg = gdocs(ledger)
                if sid in reg["sessions"]:
                    raise EventError("session doc %s is already registered" % sid)
                reg["sessions"][sid] = {k: payload.get(k) for k in ("doc_id", "url", "title", "summary",
                                                                     "tags", "date", "indexed")}
                reg["sessions"][sid].update({"opened": date, "closed": bool(payload.get("closed")),
                                             "recorded": bool(payload.get("recorded"))})
                meta = ledger.setdefault("log", {"file": L.LOG_FILENAME})
                if L.id_num(sid) > L.id_num(meta.get("last_id")):
                    meta["last_id"] = sid
                res = {"ok": True, "log_id": sid}
            elif etype == "logdoc-update":
                reg = gdocs(ledger)
                sid = payload["log_id"]
                if sid not in reg["sessions"]:
                    raise EventError("no session doc %s" % sid)
                reg["sessions"][sid].update({k: v for k, v in payload.items() if k != "log_id"})
                res = {"ok": True, "log_id": sid}
            elif etype == "blueprint-cache":
                if not isinstance(payload.get("text"), str) or not payload["text"].strip():
                    raise EventError("blueprint-cache needs the blueprint 'text'")
                gdocs(ledger)["blueprint_cache"] = {
                    "text": payload["text"], "modified": payload.get("modified"),
                    "doc_id": payload.get("doc_id"), "cached": date,
                    "sha256": hashlib.sha256(payload["text"].encode("utf-8")).hexdigest()}
                res = {"ok": True, "chars": len(payload["text"]), "modified": payload.get("modified")}
            elif etype == "doc-state":
                _set_doc_state(ledger, payload.get("doc") or "index", payload)
                res = {"ok": True, "doc": payload.get("doc") or "index"}
        if etype == "resolve-conflict":
            res = {"ok": True, "resolved_seq": payload.get("seq"), "kept": payload.get("keep_sha")}
        if etype == "record":
            sid = (payload.get("round") or {}).get("log_id") or res.get("log_id")
            reg = gdocs(ledger)
            if sid in reg["sessions"]:
                reg["sessions"][sid]["recorded"] = True
                if payload.get("close_log"):
                    reg["sessions"][sid]["closed"] = True
        return ledger, res
    finally:
        for f in (lp, pp):
            if os.path.exists(f):
                os.remove(f)
        os.rmdir(tmpdir)


def gdocs(ledger):
    reg = ledger.setdefault("gdocs", {})
    reg.setdefault("sessions", {})
    return reg


def _set_doc_state(ledger, name, state):
    """Remember where a doc ends and its revision after our last write, so the next write can
    be built without reading the doc first. Only valid together with a revision: the write is
    then guarded and is rejected (and rebuilt from a fresh read) if anything else changed it."""
    st = {k: state.get(k) for k in ("end_index", "revision") if state.get(k) is not None}
    if st.get("end_index") is not None:
        st["end_index"] = int(st["end_index"])
    gdocs(ledger).setdefault("doc_state", {})[name] = st


def replay_sources(paths):
    all_events, errors, warnings, sources = [], [], [], []
    for p in paths:
        g = load_gdoc(p)
        ev, er, wa = parse_journal_text(g["text"], os.path.basename(p))
        all_events += ev
        errors += er
        warnings += wa
        sources.append({"path": p, "kind": g["kind"], "doc_id": g["doc_id"], "title": g["title"],
                        "revision": g["revision"], "end_index": g["end_index"],
                        "chars": len(g["text"]), "events": len(ev),
                        "last_seq": max([e["seq"] for e in ev] + [0])})
    events, er, wa = order_events(all_events)
    errors += er
    warnings += wa
    return events, errors, warnings, sources


def cmd_journal_replay(args):
    events, errors, warnings, sources = replay_sources(args.journal)
    if errors and not args.force:
        die("journal problems: %s" % "; ".join(errors[:6]))
    ledger = None
    for e in events:
        try:
            ledger, _ = apply_event(ledger, e["type"], e["date"], e["payload"])
        except EventError as exc:
            die("event %06d (%s, %s) could not be applied: %s" % (e["seq"], e["type"], e["date"], exc))
    if ledger is None:
        die("the journal has no events yet")
    size = L.save_ledger(ledger, args.out)
    last = sources[-1] if sources else {}
    reg = ledger.get("gdocs") or {}
    bp = reg.get("blueprint_cache") or {}
    blueprint = {"cached": bool(bp.get("text")), "modified": bp.get("modified"),
                 "fresh": None, "out": None}
    if bp.get("text") and args.blueprint_modified:
        blueprint["fresh"] = bp.get("modified") == args.blueprint_modified
    if bp.get("text") and args.blueprint_out and blueprint["fresh"] is not False:
        write_file(args.blueprint_out, bp["text"])
        blueprint["out"] = args.blueprint_out
    if not blueprint["out"]:
        blueprint["note"] = ("No usable cached blueprint: download the blueprint doc as text "
                             "and add a blueprint-cache event to this session's journal write.")
    storage = (ledger.get("config") or {}).get("storage") or {}
    print(json.dumps({
        "ok": True, "out": args.out, "bytes": size, "events": len(events),
        "last_seq": events[-1]["seq"] if events else 0,
        "next_seq": (events[-1]["seq"] if events else 0) + 1,
        "ledger_sha256": digest(ledger),
        "last_volume": {k: last.get(k) for k in ("path", "doc_id", "revision", "end_index", "chars", "kind")},
        "rollover_recommended": bool(last.get("chars", 0) > ROLLOVER_CHARS),
        "blueprint": blueprint,
        "doc_state": reg.get("doc_state") or {},
        "ids": {k: storage.get(k) for k in ("folder_id", "sessions_folder_id", "index_id",
                                            "blueprint_id", "library_id", "journal_ids")},
        "sources": sources, "errors": errors, "warnings": warnings}, indent=2, ensure_ascii=False))


def _parse_also(spec):
    if ":" not in spec:
        die("--also must look like TYPE:PAYLOAD (PAYLOAD is inline JSON or a file path)")
    etype, raw = spec.split(":", 1)
    etype = etype.strip()
    if etype not in EVENT_TYPES:
        die("--also: unknown event type %s" % etype)
    return etype, (L.load_json_arg(raw) if raw.strip() else {})


def _guard(args):
    """Optional revision guard: from a saved read (--doc) or from --revision."""
    if getattr(args, "doc", None):
        g = load_gdoc(args.doc)
        if g["kind"] != "read_doc":
            die("--doc must be a saved read_doc result; or pass --revision instead")
        return g
    if getattr(args, "revision", None):
        return {"kind": "args", "revision": args.revision,
                "end_index": getattr(args, "end_index", None), "text": None}
    return None


def cmd_journal_make(args):
    payload = L.load_json_arg(args.payload) if args.payload else {}
    if args.type == "record" and "round" not in payload:
        payload = {"round": payload}
    if args.type == "record" and args.close_log:
        payload["close_log"] = True
    if args.type == "record" and args.logdoc:
        payload["logdoc"] = L.load_json_arg(args.logdoc)
    if args.type == "record" and args.index_state:
        payload["index_state"] = L.load_json_arg(args.index_state)
    if args.type == "review" and "review" not in payload:
        payload = {"review": payload}
    date = args.date or L.iso(dt.date.today())
    ledger = L.load_json(args.ledger) if args.ledger and os.path.exists(args.ledger) else None
    if args.type not in ("init", "import") and ledger is None:
        die("--ledger (the working ledger from journal-replay) is required for %s" % args.type)
    before = digest(ledger) if ledger is not None else None
    events = [(args.type, payload)] + [_parse_also(x) for x in args.also or []]
    new, results, lines = copy.deepcopy(ledger), [], []
    for k, (etype, pl) in enumerate(events):
        try:
            new, res = apply_event(new, etype, date, pl)
        except EventError as exc:
            die("this change cannot be applied (%s): %s" % (etype, exc))
        results.append(res)
        lines.append(event_line(args.seq + k, date, etype, pl))
    text = "\n" + "\n".join(lines)
    out = {"ok": True, "seq": args.seq, "types": [e[0] for e in events],
           "next_seq_after": args.seq + len(events), "line_chars": len(text),
           "ledger_before_sha256": before, "ledger_after_sha256": digest(new),
           "result": results[0]}
    if len(results) > 1:
        out["also_results"] = results[1:]
    if args.out:
        out["ledger_out"] = args.out
        L.save_ledger(new, args.out)
    if not args.dry_run:
        # Appended at the end of the body: no read of the journal is needed before the write.
        # Two sessions writing at once produce two events with one number, which replay
        # reports (google_drive.md section 9); a revision guard is added when one is given.
        req = {"insertText": {"endOfSegmentLocation": {}, "text": text}}
        out["update_doc"] = {"requests": [req]}
        g = _guard(args)
        if g:
            out["update_doc"]["writeControl"] = {"requiredRevisionId": g["revision"]}
            if g.get("text") is not None:
                out["journal_chars_after"] = len(g["text"]) + len(text)
                out["rollover_recommended"] = out["journal_chars_after"] > ROLLOVER_CHARS
    if args.line_out:
        write_file(args.line_out, "\n".join(lines) + "\n")
        out["line_out"] = args.line_out
    if args.print_line:
        out["lines"] = lines
    print(json.dumps(out, indent=2, ensure_ascii=False))


# ------------------------------------------------------------------ Markdown -> HTML

INLINE_RE = re.compile(r"(\*\*(.+?)\*\*(?!\*)|\[([^\]]+)\]\((https?://[^)\s]+)\)|`([^`]+)`|(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*]))")


def inline_html(text):
    out, pos = [], 0
    for m in INLINE_RE.finditer(text):
        out.append(html.escape(text[pos:m.start()], quote=False))
        if m.group(2) is not None:
            out.append("<b>%s</b>" % inline_html(m.group(2)))
        elif m.group(3) is not None:
            out.append('<a href="%s">%s</a>' % (html.escape(m.group(4)), html.escape(m.group(3), quote=False)))
        elif m.group(5) is not None:
            out.append("<code>%s</code>" % html.escape(m.group(5), quote=False))
        else:
            out.append("<i>%s</i>" % inline_html(m.group(6)))
        pos = m.end()
    out.append(html.escape(text[pos:], quote=False))
    return "".join(out)


def md_to_html(md, heading_shift=0):
    lines = md.replace("\r\n", "\n").split("\n")
    out, i, para = [], 0, []
    list_kind = None

    def flush_para():
        nonlocal para
        if para:
            out.append("<p>%s</p>" % inline_html(" ".join(x.strip() for x in para)))
            para = []

    def close_list():
        nonlocal list_kind
        if list_kind:
            out.append("</%s>" % list_kind)
            list_kind = None

    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if s.startswith("<!--") and s.endswith("-->"):
            i += 1
            continue
        if not s:
            flush_para(); close_list(); i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            flush_para(); close_list()
            lvl = max(1, min(6, len(m.group(1)) + heading_shift))
            out.append("<h%d>%s</h%d>" % (lvl, inline_html(m.group(2)), lvl))
            i += 1
            continue
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\|?\s*:?-{2,}", lines[i + 1].strip()):
            flush_para(); close_list()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
            body = [c for k, c in enumerate(cells) if k != 1]
            t = ["<table>"]
            for k, row in enumerate(body):
                tag = "th" if k == 0 else "td"
                t.append("<tr>" + "".join("<%s>%s</%s>" % (tag, inline_html(c), tag) for c in row) + "</tr>")
            t.append("</table>")
            out.append("".join(t))
            continue
        if re.match(r"^(-{3,}|\*{3,})$", s):
            flush_para(); close_list(); out.append("<hr>"); i += 1
            continue
        m = re.match(r"^\s*([-*•]|\d+[.)])\s+(.*)$", line)
        if m:
            flush_para()
            kind = "ol" if m.group(1)[0].isdigit() else "ul"
            if list_kind != kind:
                close_list(); out.append("<%s>" % kind); list_kind = kind
            out.append("<li>%s</li>" % inline_html(m.group(2)))
            i += 1
            continue
        if s.startswith(">"):
            flush_para(); close_list()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            out.append("<blockquote><p>%s</p></blockquote>" % inline_html(" ".join(quote)))
            continue
        close_list()
        para.append(line)
        i += 1
    flush_para(); close_list()
    return "".join(out)


def session_header_md(sid, date, title, summary, tags, meta):
    lines = ["# %s · %s · %s" % (sid, date, title.strip()), "",
             "**Summary:** %s" % " ".join(summary.split()), "",
             "**Tags:** %s" % L.clean_tags(tags)]
    if meta:
        lines += ["", "**Session:** %s" % " · ".join(m.strip() for m in meta.split("|") if m.strip())]
    return "\n".join(lines) + "\n"


def pending_line(sid):
    return ("%s %s — the reflection, discussion and coded analysis are added at the end of the "
            "session." % (PENDING_TAG, sid))


def entry_from_log(log_path, sid):
    """(header fields, body) of one entry of a local session log, for migration."""
    text = L.read_text(log_path)
    if text is None:
        die("log not found: %s" % log_path)
    parsed = L.parse_log(text)
    blocks = [b for b in parsed["blocks"] if b["id"] == sid]
    entry = next((b for b in blocks if b["kind"] == "entry"), None)
    if not entry:
        die("no entry %s in the log" % sid)
    body_lines = []
    for b in blocks:
        for line in parsed["lines"][b["start"]:b["end"] + 1]:
            if L.MARKER.search(line) or L.RE_HEAD.match(line) or line.startswith(("**Summary:**", "**Tags:**", "**Session:**")):
                continue
            body_lines.append(line)
    meta = next((l[len("**Session:**"):].strip() for l in parsed["lines"][entry["start"]:entry["end"] + 1]
                 if l.startswith("**Session:**")), "")
    return {"date": entry["date"], "title": entry["title"], "summary": entry["summary"] or "",
            "tags": " ".join(entry["tags"]), "meta": meta.replace(" · ", "|"),
            "complete": entry["closed"]}, "\n".join(body_lines)


def cmd_gdoc_frame(args):
    """The fixed start and end of a session doc, as HTML, so part A can be written straight
    into the create_file call (one pass) instead of being written to a file first."""
    if not all([args.session, args.date, args.title, args.summary]):
        die("gdoc-frame needs --session, --date, --title and --summary")
    head = md_to_html(session_header_md(args.session, args.date, args.title, args.summary,
                                        args.tags or "", args.meta))
    foot = "" if args.complete else md_to_html(pending_line(args.session))
    print(json.dumps({"ok": True, "doc_title": "%s · %s · %s" % (args.session, args.date, args.title.strip()),
                      "header_html": head, "footer_html": foot,
                      "check": {"contains": ["%s · %s · %s" % (args.session, args.date, args.title.strip())]
                                + ([PENDING_TAG + " " + args.session] if foot else [])}},
                     indent=2, ensure_ascii=False))


def cmd_gdoc_html(args):
    body = read_file(args.body) if args.body else ""
    if args.from_log:
        if not args.session:
            die("--from-log needs --session")
        fields, body = entry_from_log(args.from_log, args.session)
        for k in ("date", "title", "summary", "tags", "meta"):
            if not getattr(args, k):
                setattr(args, k, fields[k])
        args.complete = args.complete or fields["complete"]
    if L.MARKER.search(body):
        body = "\n".join(l for l in body.split("\n") if not L.MARKER.search(l))
    if args.mode == "session":
        if not all([args.session, args.date, args.title, args.summary]):
            die("session mode needs --session, --date, --title and --summary")
        md = session_header_md(args.session, args.date, args.title, args.summary, args.tags or "", args.meta)
        # '###' section headings in the log format become level-2 headings in a session doc
        md += "\n" + re.sub(r"^###(?=\s)", "##", body, flags=re.M)
        if not args.complete:
            md += "\n\n" + pending_line(args.session) + "\n"
        title = "%s · %s · %s" % (args.session, args.date, args.title.strip())
    else:
        md = body
        title = args.title or "Untitled"
    out_html = md_to_html(md)
    write_file(args.out, out_html)
    print(json.dumps({"ok": True, "out": args.out, "doc_title": title, "html_chars": len(out_html),
                      "note": "Create the Google Doc from this HTML (Drive create_file, text/html), "
                              "in the right folder, with doc_title as its name."}, indent=2,
                     ensure_ascii=False))


# ------------------------------------------------------------------ styled appends

def md_paragraphs(md):
    """Markdown -> [(kind, level, text, spans)] where spans = [(start, end, 'bold'|('link', url))]."""
    out = []
    lines = md.replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lines):
        raw = lines[i]
        s = raw.strip()
        i += 1
        if s.startswith("<!--") and s.endswith("-->"):
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            kind, level, text = "heading", min(6, len(m.group(1))), m.group(2)
        else:
            m = re.match(r"^\s*[-*•]\s+(.*)$", raw)
            if m:
                kind, level, text = "bullet", 0, m.group(1)
            else:
                kind, level, text = "normal", 0, raw.rstrip()
        plain, spans = strip_inline(text)
        out.append((kind, level, plain, spans))
    while out and out[-1][2] == "" and out[-1][0] == "normal":
        out.pop()
    while out and out[0][2] == "" and out[0][0] == "normal":
        out.pop(0)
    return out


def strip_inline(text):
    """Remove **bold** and [link](url) markers; return (plain, spans) with UTF-16 offsets.
    Handles a link inside bold (**[title](url)**) and bold inside a link label."""
    spans, out, pos = [], [], 0
    for m in re.finditer(r"\*\*(.+?)\*\*|\[([^\]]+)\]\((https?://[^)\s]+)\)", text):
        out.append(text[pos:m.start()])
        start = utf16len("".join(out))
        if m.group(1) is not None:
            inner, inner_spans = strip_inline(m.group(1))
            out.append(inner)
            spans.append((start, start + utf16len(inner), "bold"))
        else:
            inner, inner_spans = strip_inline(m.group(2))
            out.append(inner)
            spans.append((start, start + utf16len(inner), ("link", m.group(3))))
        spans += [(start + a, start + b, w) for a, b, w in inner_spans]
        pos = m.end()
    out.append(text[pos:])
    return "".join(out), spans


def build_append(g, md, replace_pending=None, heading_shift=0, start_new_paragraph=True):
    """update_doc requests that add Markdown as styled paragraphs.

    g is a doc state: a saved read (load_gdoc, with paragraphs) or {"end_index", "revision"}
    from arguments or from the ledger's doc_state (no paragraphs, no text).
    Returns (requests, joined_text, end_index_after)."""
    pars = md_paragraphs(md)
    if not pars:
        die("nothing to append")
    joined = "\n".join(p[2] for p in pars)
    requests, tail = [], None
    end = int(g["end_index"])
    have_pars = g.get("paragraphs") is not None
    if replace_pending and have_pars:
        target = next((p for p in g["paragraphs"] or []
                       if (PENDING_TAG + " " + replace_pending) in p["text"]), None)
        if not target:
            die("the pending marker for %s is not in this doc (already completed?)" % replace_pending)
        start = target["start"]
        removed = max(0, target["end"] - 1 - start)
        if removed:
            requests.append({"deleteContentRange": {"range": {"startIndex": start,
                                                              "endIndex": target["end"] - 1}}})
        text, first = joined, start
        end_after = end - removed + utf16len(joined)
    elif replace_pending:
        # No paragraph positions (the read came back inline): append at the end, styled, and
        # only then blank the marker with replaceAllText (the last request), so the positions
        # used for styling are not shifted by the removal. The revision guard keeps it exact.
        marker = pending_line(replace_pending)
        start = end - 1
        text, first = "\n" + joined, start + 1
        end_after = end + utf16len(text) - utf16len(marker)
        tail = {"replaceAllText": {"containsText": {"text": marker, "matchCase": True},
                                   "replaceText": ""}}
    else:
        start = end - 1
        nonempty = g["text"].strip() if g.get("text") is not None else True
        lead = "\n" if start_new_paragraph and nonempty else ""
        text, first = lead + joined, start + utf16len(lead)
        end_after = end + utf16len(text)
    requests.append({"insertText": {"location": {"index": start}, "text": text}})
    total = utf16len(joined)
    span = max(total, 1)
    requests.append({"updateParagraphStyle": {"range": {"startIndex": first, "endIndex": first + span},
                                              "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                                              "fields": "namedStyleType"}})
    requests.append({"deleteParagraphBullets": {"range": {"startIndex": first, "endIndex": first + span}}})
    requests.append({"updateTextStyle": {"range": {"startIndex": first, "endIndex": first + max(total, 1)},
                                         "textStyle": {}, "fields": "bold,italic,link"}})
    pos = first
    bullets = []
    for kind, level, plain, spans in pars:
        n = utf16len(plain)
        if kind == "heading" and n:
            lvl = max(1, min(6, level + heading_shift))
            requests.append({"updateParagraphStyle": {"range": {"startIndex": pos, "endIndex": pos + n},
                                                      "paragraphStyle": {"namedStyleType": "HEADING_%d" % lvl},
                                                      "fields": "namedStyleType"}})
        if kind == "bullet" and n:
            if bullets and bullets[-1][1] == pos - 1:
                bullets[-1][1] = pos + n
            else:
                bullets.append([pos, pos + n])
        for a, b, what in spans:
            if b <= a:
                continue
            if what == "bold":
                requests.append({"updateTextStyle": {"range": {"startIndex": pos + a, "endIndex": pos + b},
                                                     "textStyle": {"bold": True}, "fields": "bold"}})
            else:
                requests.append({"updateTextStyle": {"range": {"startIndex": pos + a, "endIndex": pos + b},
                                                     "textStyle": {"link": {"url": what[1]}}, "fields": "link"}})
        pos += n + 1
    for a, b in bullets:
        requests.append({"createParagraphBullets": {"range": {"startIndex": a, "endIndex": b},
                                                    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"}})
    if tail:
        requests.append(tail)
    return requests, joined, end_after


def index_line(entry):
    """The index doc line for one session (same JSON as journal-make --logdoc)."""
    for k in ("log_id", "date", "title", "url"):
        if not entry.get(k):
            die("--index-entry needs %s" % k)
    tags = L.clean_tags(entry.get("tags") or "")
    tags = " ".join("#" + t.lstrip("#") for t in tags.split()) if tags else ""
    line = "**[%s · %s · %s](%s)**" % (entry["log_id"], entry["date"], " ".join(entry["title"].split()),
                                      entry["url"])
    if entry.get("summary"):
        line += " — " + " ".join(str(entry["summary"]).split())
    if tags:
        line += " · " + tags
    return line


def doc_state_arg(args, name=None):
    """Doc state for a write: a saved read (--doc), explicit --revision/--end-index, or the
    state the ledger remembers for this doc (--ledger with --state-name)."""
    if getattr(args, "doc", None):
        g = load_gdoc(args.doc)
        if g["kind"] != "read_doc":
            die("--doc must be a saved read_doc result; for an inline read pass --revision and --end-index")
        g["source"] = "read"
        return g
    if getattr(args, "revision", None) and getattr(args, "end_index", None):
        return {"kind": "args", "revision": args.revision, "end_index": int(args.end_index),
                "text": None, "paragraphs": None, "doc_id": None, "source": "args"}
    if getattr(args, "ledger", None) and name:
        st = ((L.load_json(args.ledger).get("gdocs") or {}).get("doc_state") or {}).get(name) or {}
        if st.get("revision") and st.get("end_index"):
            return {"kind": "args", "revision": st["revision"], "end_index": int(st["end_index"]),
                    "text": None, "paragraphs": None, "doc_id": None, "source": "ledger"}
        die("no remembered state for the %s doc: read it once with read_doc and pass --doc "
            "(saved) or --revision and --end-index (inline)" % name)
    die("give --doc (saved read), or --revision and --end-index")


def cmd_gdoc_append(args):
    g = doc_state_arg(args, args.state_name)
    if args.index_entry:
        md = index_line(L.load_json_arg(args.index_entry))
    elif args.line is not None:
        md = args.line
    elif args.body:
        md = read_file(args.body)
    else:
        die("give --body FILE, --line TEXT or --index-entry JSON")
    if L.MARKER.search(md):
        md = "\n".join(l for l in md.split("\n") if not L.MARKER.search(l))
    md = re.sub(r"^###(?=\s)", "##", md, flags=re.M) if args.session_sections else md
    requests, joined, end_after = build_append(g, md, args.replace_pending)
    out = {"ok": True, "doc_id": g.get("doc_id"), "state_source": g.get("source"),
           "chars_added": len(joined),
           "update_doc": {"requests": requests,
                          "writeControl": {"requiredRevisionId": g["revision"]}},
           "state_after": {"end_index": end_after,
                           "revision": "<writeControl.requiredRevisionId from the update_doc response>"}}
    if g.get("text") is not None:
        out["doc_chars_after"] = len(g["text"]) + len(joined)
    if args.index_entry:
        out["line"] = md
    print(json.dumps(out, indent=2, ensure_ascii=False))


def cmd_gdoc_insert(args):
    text = read_file(args.text).rstrip("\n")
    g = _guard(args)
    if g and g.get("text") is not None and not g["text"].strip():
        lead = ""
    else:
        lead = "\n"
    upd = {"requests": [{"insertText": {"endOfSegmentLocation": {}, "text": lead + text}}]}
    if g:
        upd["writeControl"] = {"requiredRevisionId": g["revision"]}
    if args.empty_doc:
        upd["requests"][0]["insertText"]["text"] = text
    print(json.dumps({"ok": True, "chars_added": len(upd["requests"][0]["insertText"]["text"]),
                      "update_doc": upd}, indent=2, ensure_ascii=False))


_BULLET_LEAD = re.compile(r"(?m)^[ \t]*(?:[*\-\u2022\u25cf\u25cb\u25a0\u25aa\u2023\u2043]|\d+[.)])[ \t]+")


def _norm(s):
    return re.sub(r"\s+", " ", s).strip()


def cmd_gdoc_verify(args):
    g = load_gdoc(args.doc)
    problems = []
    text = g["text"]
    if args.expect:
        md = read_file(args.expect)
        if args.session_sections:
            md = re.sub(r"^###(?=\s)", "##", md, flags=re.M)
        # A plain-text export (download_file_content) shows bullets as "* " or "●"; a read_doc
        # does not. Leading bullet and list markers are ignored on both sides.
        if args.literal:
            want = _norm(_BULLET_LEAD.sub("", md))
        else:
            want = _norm(_BULLET_LEAD.sub("", "\n".join(p[2] for p in md_paragraphs(md))))
        got = _norm(_BULLET_LEAD.sub("", text))
        if args.anywhere:
            if want not in got:
                problems.append("the expected text is not in the doc")
        elif not got.endswith(want):
            problems.append("the doc does not end with the expected text")
    for sid in args.no_pending or []:
        if (PENDING_TAG + " " + sid) in text:
            problems.append("the pending marker for %s is still there" % sid)
    for frag in args.contains or []:
        if _norm(frag) not in _norm(text):
            problems.append("missing: %s" % frag[:80])
    pending_last = None
    if g.get("paragraphs"):
        nonempty = [p for p in g["paragraphs"] if p["text"].strip()]
        pending_last = bool(nonempty) and nonempty[-1]["text"].strip().startswith(PENDING_TAG)
    print(json.dumps({"ok": not problems, "problems": problems, "kind": g["kind"],
                      "revision": g["revision"], "end_index": g["end_index"], "chars": len(text),
                      "pending_markers": re.findall(PENDING_TAG + r" (S\d{3,})", text),
                      "pending_is_last": pending_last,
                      "state": {"end_index": g["end_index"], "revision": g["revision"]}
                      if g["kind"] == "read_doc" else None}, indent=2, ensure_ascii=False))
    sys.exit(0 if not problems else 1)


# ------------------------------------------------------------------ review and backfill

def cmd_gdoc_period(args):
    ledger = L.load_json(args.ledger)
    prof = ledger.get("profile") or {}
    start, inclusive = L.review_window(prof, L.parse_date(args.since))
    if args.all:
        start, inclusive = None, True
    reg = gdocs(ledger)["sessions"]
    rows, seen_docs = [], set()
    for sid in sorted(reg, key=L.id_num):
        r = reg[sid]
        if not L.in_window(r.get("date"), start, inclusive):
            continue
        rows.append({"log_id": sid, "date": r.get("date"), "title": r.get("title"),
                     "doc_id": r.get("doc_id"), "url": r.get("url"),
                     "recorded": r.get("recorded"), "complete": r.get("closed"),
                     "reconstructed": bool(r.get("reconstructed")),
                     "read": r.get("doc_id") not in seen_docs})
        seen_docs.add(r.get("doc_id"))
    batches = []
    to_read = [r for r in rows if r["read"] and not r["reconstructed"]]
    for k in range(0, len(to_read), args.batch):
        batches.append([r["log_id"] for r in to_read[k:k + args.batch]])
    print(json.dumps({"ok": True, "period_start": L.iso(start), "count": len(rows),
                      "docs_to_read": len(to_read), "batches": batches, "sessions": rows,
                      "folder_id": (ledger.get("config", {}).get("storage") or {}).get("sessions_folder_id")},
                     indent=2, ensure_ascii=False))


def cmd_gdoc_backfill(args):
    ledger = L.load_json(args.ledger)
    topics = ledger.get("topics") or {}
    todo = [(i, s) for i, s in enumerate(L.sessions(ledger)) if not s.get("log_id")]
    if not todo:
        die("every session already has a log id; nothing to backfill")
    md = ["# Reconstructed sessions (before version 3)", "",
          "These sessions were recorded before the skill kept a full log. Each stub is rebuilt "
          "from the ledger: topics, scores, reflection and key learning. The cases, answers and "
          "feedback were not kept.", ""]
    index = []
    for i, s in todo:
        sid = "S%04d" % (i + 1)
        labels = [(topics.get(t) or {}).get("label") or t for t in s.get("topic_ids") or []]
        title = "Reconstructed: " + "; ".join(labels[:3]) if labels else "Reconstructed session"
        md += ["## %s · %s · %s" % (sid, s.get("date"), title), ""]
        md += [l for l in L._stub_body(ledger, s).split("\n")
               if not l.startswith("### Reconstructed record")] + [""]
        summary = (s.get("key_learning") or ["Session recorded before the full log existed."])[0]
        index.append("**%s · %s · %s** — %s · tags: %s #reconstructed" % (
            sid, s.get("date"), title, " ".join(str(summary).split()),
            " ".join("#" + t for t in s.get("topic_ids") or [])))
    write_file(args.out_html, md_to_html("\n".join(md)))
    write_file(args.out_index, "\n".join(index) + "\n")
    print(json.dumps({"ok": True, "sessions": len(todo), "ids": ["S%04d" % (i + 1) for i, _ in todo],
                      "doc_title": "S0001–S%04d · Reconstructed sessions (before version 3)" % (todo[-1][0] + 1),
                      "out_html": args.out_html, "out_index": args.out_index,
                      "next": "Create the doc in the Sessions folder, append the index lines (with the "
                              "doc's link added to each), then journal a 'backfill' event with "
                              "{doc_id, url}."}, indent=2, ensure_ascii=False))


# ------------------------------------------------------------------ main

def main(argv=None):
    p = argparse.ArgumentParser(description="Google Drive home for the clinical-cme skill.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("journal-replay"); s.add_argument("journal", nargs="+")
    s.add_argument("--out", required=True); s.add_argument("--force", action="store_true")
    s.add_argument("--blueprint-out", help="write the cached blueprint text here (if fresh)")
    s.add_argument("--blueprint-modified", help="the blueprint doc's modifiedTime from the Drive search")
    s.set_defaults(fn=cmd_journal_replay)

    s = sub.add_parser("journal-make")
    s.add_argument("--type", required=True, choices=EVENT_TYPES)
    s.add_argument("--seq", required=True, type=int, help="next_seq from journal-replay")
    s.add_argument("--date", help="the session date (YYYY-MM-DD)")
    s.add_argument("--payload", help="event JSON (inline or path); for record, the round JSON")
    s.add_argument("--ledger", help="working ledger from journal-replay")
    s.add_argument("--out", help="write the updated working ledger here")
    s.add_argument("--doc", help="optional saved read_doc of the last volume: adds a revision guard")
    s.add_argument("--revision", help="optional revision guard (from an inline read)")
    s.add_argument("--dry-run", action="store_true", help="apply and report only; no update_doc")
    s.add_argument("--also", action="append", metavar="TYPE:PAYLOAD",
                   help="further events in the same write (e.g. blueprint-cache:bp.json)")
    s.add_argument("--logdoc", help="record: register the session doc (JSON: log_id, doc_id, url, "
                                    "title, summary, tags, date, indexed)")
    s.add_argument("--index-state", help="record: index doc state after this session's index write "
                                         "(JSON: end_index, revision)")
    s.add_argument("--line-out"); s.add_argument("--close-log", action="store_true")
    s.add_argument("--print-line", action="store_true", help="also print the journal lines")
    s.set_defaults(fn=cmd_journal_make)

    s = sub.add_parser("gdoc-text"); s.add_argument("doc"); s.add_argument("--out")
    s.add_argument("--markdown", action="store_true", help="prefix headings with # and bullets with -")
    s.add_argument("--cache-json", help="also write a blueprint-cache event payload here")
    s.add_argument("--modified", help="with --cache-json: the doc's modifiedTime from the search")
    s.add_argument("--doc-id", help="with --cache-json: the doc's ID")
    s.set_defaults(fn=cmd_gdoc_text)

    s = sub.add_parser("gdoc-html"); s.add_argument("--mode", choices=["session", "doc"], default="session")
    s.add_argument("--body"); s.add_argument("--out", required=True)
    s.add_argument("--session"); s.add_argument("--date"); s.add_argument("--title")
    s.add_argument("--summary"); s.add_argument("--tags"); s.add_argument("--meta")
    s.add_argument("--complete", action="store_true", help="no pending marker (whole entry at once)")
    s.add_argument("--from-log", help="a local CME_session_log.md: convert entry --session (migration)")
    s.set_defaults(fn=cmd_gdoc_html)

    s = sub.add_parser("gdoc-frame")
    s.add_argument("--session"); s.add_argument("--date"); s.add_argument("--title")
    s.add_argument("--summary"); s.add_argument("--tags"); s.add_argument("--meta")
    s.add_argument("--complete", action="store_true", help="no pending marker")
    s.set_defaults(fn=cmd_gdoc_frame)

    s = sub.add_parser("gdoc-append"); s.add_argument("--doc", help="saved read_doc result")
    s.add_argument("--revision"); s.add_argument("--end-index", type=int)
    s.add_argument("--ledger", help="use the doc state remembered in this ledger (--state-name)")
    s.add_argument("--state-name", help="which remembered doc state to use, e.g. index")
    s.add_argument("--body"); s.add_argument("--line", help="one line of Markdown instead of --body")
    s.add_argument("--index-entry", help="build the index line from this JSON (same as --logdoc)")
    s.add_argument("--replace-pending")
    s.add_argument("--session-sections", action="store_true", help="turn ### headings into ##")
    s.set_defaults(fn=cmd_gdoc_append)

    s = sub.add_parser("gdoc-insert"); s.add_argument("--doc", help="optional saved read: adds a guard")
    s.add_argument("--revision", help="optional revision guard")
    s.add_argument("--empty-doc", action="store_true", help="the doc is new and empty: no leading newline")
    s.add_argument("--text", required=True); s.set_defaults(fn=cmd_gdoc_insert)

    s = sub.add_parser("gdoc-verify"); s.add_argument("--doc", required=True)
    s.add_argument("--expect"); s.add_argument("--literal", action="store_true")
    s.add_argument("--anywhere", action="store_true"); s.add_argument("--session-sections", action="store_true")
    s.add_argument("--no-pending", nargs="*"); s.add_argument("--contains", nargs="*")
    s.set_defaults(fn=cmd_gdoc_verify)

    s = sub.add_parser("gdoc-period"); s.add_argument("ledger"); s.add_argument("--since")
    s.add_argument("--all", action="store_true"); s.add_argument("--batch", type=int, default=6)
    s.set_defaults(fn=cmd_gdoc_period)

    s = sub.add_parser("gdoc-backfill"); s.add_argument("ledger")
    s.add_argument("--out-html", required=True); s.add_argument("--out-index", required=True)
    s.set_defaults(fn=cmd_gdoc_backfill)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
