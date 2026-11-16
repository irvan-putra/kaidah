"""pandu: a shared decision/permission log, status page and grant templates.

Standard library only. Data is private by default and lives in a local
directory (PANDU_DIR, default ./.pandu). Every event is its own small,
immutable JSON file in events/, named by a unique event id. Nothing is ever
edited or deleted: corrections and resolutions are new events.

Order never comes from clocks. Each event names the event(s) it was based on
(its parents), so the history is a graph. If two people change the same entry
from the same starting point, the entry is in CONFLICT: it is shown for
attention, counts as neither active nor valid, and needs an explicit `settle`.
Nothing is silently merged, extended or revived.

This is a local tool: it does not enforce permissions, remove access or send
notifications. The log is an index; the linked evidence wins if they disagree.
"""
import argparse, datetime as dt, hashlib, html, json, os, re, subprocess, sys, tempfile, uuid

KINDS = ("agreed", "waiting", "approval", "work")
RESOLUTIONS = ("approved", "denied", "done", "expired", "revoked", "archived")
WORK_STATES = ("running", "done", "blocked")
FIELD_KEYS = ("title", "scope", "conditions", "expires", "evidence", "waiting_on",
              "next_actor", "state", "notes")
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.environ.get("PANDU_TEMPLATES", os.path.join(HERE, "..", "templates"))


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def die(msg):
    sys.exit("error: " + msg)


def data_dir():
    d = os.environ.get("PANDU_DIR", ".pandu")
    if not os.path.isdir(d):
        os.makedirs(d, mode=0o700, exist_ok=True)
        os.chmod(d, 0o700)
    return d


def events_dir():
    d = os.path.join(data_dir(), "events")
    if not os.path.isdir(d):
        os.makedirs(d, mode=0o700, exist_ok=True)
        os.chmod(d, 0o700)
    return d


def write_event(ev, ident=None):
    """Create events/<id>.json without ever overwriting. Returns the event id.

    A fixed id (used by sweep, so two machines produce the identical file) may
    already exist with identical content, which is fine. Different content is an error."""
    ident = ident or uuid.uuid4().hex[:16]
    ev = dict(ev, eid=ident)
    body = json.dumps(ev, sort_keys=True, indent=1) + "\n"
    final = os.path.join(events_dir(), ident + ".json")
    fd, tmp = tempfile.mkstemp(dir=events_dir(), prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(body)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o600)
        try:
            os.link(tmp, final)
        except FileExistsError:
            with open(final, encoding="utf-8") as f:
                if f.read() != body:
                    die(f"event {ident} already exists with different content")
    finally:
        os.unlink(tmp)
    return ident


def load_events():
    d = events_dir()
    out = {}
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue  # temp files and non-events are ignored
        p = os.path.join(d, fn)
        try:
            with open(p, encoding="utf-8") as f:
                e = json.load(f)
            if (not isinstance(e, dict) or e.get("eid") != fn[:-5] or "op" not in e
                    or "entry" not in e or not isinstance(e.get("parents", []), list)):
                raise ValueError("not a valid pandu event")
        except (ValueError, OSError) as err:
            die(f"{p} is damaged ({err}). Nothing was changed. Repair or restore that file.")
        out[e["eid"]] = e
    return out


def today_date():
    """Real date. PANDU_TODAY is a TEST-ONLY override and is refused unless
    PANDU_TEST_MODE=1 is also set, so it can never quietly change what is valid."""
    t = os.environ.get("PANDU_TODAY")
    if t:
        if os.environ.get("PANDU_TEST_MODE") != "1":
            die("PANDU_TODAY is a test-only override and needs PANDU_TEST_MODE=1. "
                "Unset it to use the real date.")
        return parse_date(t)
    return dt.date.today()


def fold(evs=None):
    """Return {entry_id: entry}. Orders by parent links only, never by time.

    status is open/approved/... or 'conflict' (more than one unmerged head)."""
    evs = load_events() if evs is None else evs
    by_entry = {}
    for e in evs.values():
        by_entry.setdefault(e["entry"], {})[e["eid"]] = e
    entries = {}
    for ent, group in by_entry.items():
        if ent not in group or group[ent]["op"] != "add":
            die(f"entry {ent} has events but its 'add' event is missing (incomplete sync?). Nothing was changed.")
        for e in group.values():
            for p in e.get("parents", []):
                if p not in group:
                    die(f"event {e['eid']} refers to missing parent {p} (incomplete sync?). Nothing was changed.")
        children = {k: [] for k in group}
        for e in group.values():
            for p in e.get("parents", []):
                children[p].append(e["eid"])
        indeg = {k: len(group[k].get("parents", [])) for k in group}
        ready = sorted(k for k, v in indeg.items() if v == 0)
        order = []
        while ready:
            k = ready.pop(0)
            order.append(k)
            for c in children[k]:
                indeg[c] -= 1
                if indeg[c] == 0:
                    ready.append(c)
            ready.sort()
        if len(order) != len(group):
            die(f"entry {ent} has a cycle in its history. Nothing was changed.")
        en = {"id": ent, "status": "open", "history": []}
        for k in order:
            e = group[k]
            en["history"].append(e)
            if e["op"] == "add":
                en.update(e["fields"]); en["created"] = e["at"]
            elif e["op"] == "correct":
                en.update(e["fields"])
            elif e["op"] == "resolve":
                en["status"] = e["resolution"]
                en["resolution_note"] = e.get("note", "")
            elif e["op"] == "settle":
                en.update(e.get("fields", {}))
                en["status"] = e["status"]
                en["resolution_note"] = e.get("note", "")
        heads = sorted(k for k in group if not children[k])
        en["heads"] = heads
        if len(heads) > 1:
            en["conflict_status"] = en["status"]
            en["status"] = "conflict"
        entries[ent] = en
    # display order only: oldest first, ties by id (never used for state)
    return dict(sorted(entries.items(), key=lambda kv: (kv[1].get("created", ""), kv[0])))


def find(entries, prefix):
    m = [k for k in entries if k.startswith(prefix)]
    if len(m) != 1:
        die(f"id '{prefix}' matches {len(m)} entries")
    return m[0]


# ---- visibility: keep a public log free of private material ----
CONFIG_NAME = "pandu.json"
SKIP_KEYS = {"eid", "entry", "parents", "at", "op", "resolution", "status", "template", "kind", "state"}


LOCAL_NAME = "pandu.local.json"   # local only, never staged: holds the deny strings
LOCAL_ONLY = (LOCAL_NAME, "sent.txt")


def _read_json(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (ValueError, OSError) as err:
        die(f"{p} is damaged ({err}). Nothing was changed.")


def config():
    """visibility comes from the tracked pandu.json; deny strings from the local-only file,
    so a private name never reaches a public repository or its history."""
    d = data_dir()
    c = {"visibility": "private", "deny": []}
    p = os.path.join(d, CONFIG_NAME)
    if os.path.exists(p):
        j = _read_json(p)
        if not isinstance(j, dict) or j.get("visibility") not in ("public", "private") or "deny" in j:
            die(f"{p} is invalid (needs only a visibility; deny strings belong in {LOCAL_NAME}). Nothing was changed.")
        c["visibility"] = j["visibility"]
    p = os.path.join(d, LOCAL_NAME)
    if os.path.exists(p):
        j = _read_json(p)
        if not isinstance(j, dict) or not isinstance(j.get("deny", []), list):
            die(f"{p} is invalid. Nothing was changed.")
        c["deny"] = [x for x in j.get("deny", []) if isinstance(x, str)]
    return c


def _strings(x, key=None):
    if isinstance(x, dict):
        for k, v in x.items():
            if k not in SKIP_KEYS:
                yield from _strings(v, k)
    elif isinstance(x, list):
        for v in x:
            yield from _strings(v, key)
    elif isinstance(x, str):
        yield key, x


def public_problems(ev_like):
    """Return reasons text would be unsafe in a public log. Deterministic, deliberately
    strict: anything unclear stays out of a public log and belongs in a private one."""
    c = config()
    bad = []
    for key, text in _strings(ev_like):
        if key == "evidence" and not re.match(r"^https?://\S+$", text):
            bad.append("evidence must be a public http(s) link, not a local path, message id or description")
        for d in c["deny"]:
            if d and d.lower() in text.lower():
                bad.append(f"text contains a denied string ({d!r})")
    return bad


def public_gate(a, *payloads):
    """Public logs need --public-ok on every write and pass the checks above."""
    if config()["visibility"] != "public":
        return
    if not getattr(a, "public_ok", False):
        die("this is a PUBLIC log. Re-run with --public-ok to confirm the words are written for public readers "
            "(no private chats, names, links or sensitive details). If unsure, put it in the private log instead.")
    for p in payloads:
        bad = public_problems(p)
        if bad:
            die("not allowed in a public log: " + "; ".join(sorted(set(bad))))


def validate_public_events():
    """Pre-commit check used by sync: every event file must pass the public rules."""
    if config()["visibility"] != "public":
        return
    for eid, e in load_events().items():
        bad = public_problems(e)
        if bad:
            die(f"event {eid} is not allowed in a public log: " + "; ".join(sorted(set(bad))) +
                ". Nothing was committed or pushed.")


def _write_private_file(p, obj):
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(obj, sort_keys=True, indent=1) + "\n")


def cmd_init(a):
    d = data_dir()
    p = os.path.join(d, CONFIG_NAME)
    old = config()
    if os.path.exists(p) and old["visibility"] != a.visibility and not a.force:
        die(f"already {old['visibility']}; changing visibility needs --force (and a review of existing entries)")
    deny = set(a.deny or [])
    if not a.force:
        deny |= set(old["deny"])
    _write_private_file(p, {"visibility": a.visibility})
    _write_private_file(os.path.join(d, LOCAL_NAME), {"deny": sorted(deny)})
    gi = os.path.join(d, ".gitignore")
    have = []
    if os.path.exists(gi):
        with open(gi, encoding="utf-8") as f:
            have = f.read().splitlines()
    add = [x for x in LOCAL_ONLY if x not in have]
    if add:
        with open(gi, "a", encoding="utf-8") as f:
            f.write("".join(x + "\n" for x in add))
    print(f"{p}: {a.visibility} (deny strings stored only in {LOCAL_NAME}, which is never committed)")


def parse_date(s):
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        die(f"bad date '{s}', use YYYY-MM-DD")


def is_expired(en, today=None):
    d = parse_date(en.get("expires"))
    today = today or today_date()
    return bool(d) and en["status"] == "open" and d < today


def build_fields(a, kind):
    f = {"kind": kind}
    for k in FIELD_KEYS:
        v = getattr(a, k, None)
        if v:
            f[k] = v
    if kind == "agreed" and not f.get("evidence"):
        die("an agreed entry needs --evidence (link or pointer to the original decision)")
    if kind == "waiting" and not f.get("waiting_on"):
        die("a waiting entry needs --waiting-on")
    if kind == "work":
        f.setdefault("state", "running")
        if f["state"] not in WORK_STATES:
            die(f"state must be one of {WORK_STATES}")
    parse_date(f.get("expires"))
    return f


def new_entry(fields, extra=None):
    ev = {"op": "add", "parents": [], "fields": fields, "at": now()}
    ev.update(extra or {})
    eid = uuid.uuid4().hex[:12]
    ev["entry"] = eid
    write_event(ev, eid)
    return eid


def cmd_add(a):
    fold()  # refuse to write onto a damaged or incomplete log
    f = build_fields(a, a.kind)
    public_gate(a, f)
    print(new_entry(f))


def get_open_head(entries, prefix, verb):
    i = find(entries, prefix)
    en = entries[i]
    if en["status"] == "conflict":
        die(f"{i} is in CONFLICT (concurrent changes). Use: settle {i} ... to resolve it explicitly.")
    return i, en


def cmd_correct(a):
    entries = fold()
    i, en = get_open_head(entries, a.id, "correct")
    if en["status"] != "open":
        die(f"{i} is {en['status']}. A closed entry is never reopened by an edit; add a new entry instead.")
    f = {k: getattr(a, k) for k in FIELD_KEYS if getattr(a, k, None)}
    if not f:
        die("nothing to correct")
    if "state" in f and f["state"] not in WORK_STATES:
        die(f"state must be one of {WORK_STATES}")
    parse_date(f.get("expires"))
    old = {k: en.get(k) for k in f}
    public_gate(a, f, a.reason or "")
    write_event({"op": "correct", "entry": i, "parents": en["heads"], "fields": f,
                 "previous": old, "reason": a.reason or "", "at": now()})
    print(i)


def cmd_resolve(a):
    entries = fold()
    i, en = get_open_head(entries, a.id, "resolve")
    if en["status"] != "open" and not (en["status"] == "expired" and a.resolution == "revoked"):
        die(f"{i} is already {en['status']}")
    public_gate(a, {"note": a.note or ""})
    write_event({"op": "resolve", "entry": i, "parents": en["heads"], "resolution": a.resolution,
                 "note": a.note or "", "at": now()})
    print(i)


def cmd_settle(a):
    """Explicitly merge a conflict: the new event has every current head as parent."""
    entries = fold()
    i = find(entries, a.id)
    en = entries[i]
    if en["status"] != "conflict":
        die(f"{i} is not in conflict")
    f = {k: getattr(a, k) for k in FIELD_KEYS if getattr(a, k, None)}
    parse_date(f.get("expires"))
    public_gate(a, f, {"note": a.note or ""})
    write_event({"op": "settle", "entry": i, "parents": en["heads"], "fields": f,
                 "status": a.status, "note": a.note or "", "at": now()})
    print(i)


def cmd_sweep(a):
    """Record expired grants as expired. Deterministic: the event id comes from the
    entry, its heads and the date, so two machines sweeping the same day write the
    identical file and cannot conflict."""
    today = today_date()
    n = 0
    for i, en in fold().items():
        if is_expired(en, today):
            n += 1
            print(f"expired: {i} {en['title']} (was due {en['expires']})")
            if not a.dry_run:
                key = f"{i}|{','.join(en['heads'])}|expire|{today.isoformat()}"
                eid = hashlib.sha256(key.encode()).hexdigest()[:16]
                write_event({"op": "resolve", "entry": i, "parents": en["heads"], "resolution": "expired",
                             "note": "expiry recorded by sweep; access removal not confirmed",
                             "at": today.isoformat()}, eid)
    print(f"{n} expired entr{'y' if n == 1 else 'ies'}" + (" (dry run)" if a.dry_run else " recorded"))
    if n:
        print("note: this records the expiry only. It does not remove any access. "
              "Remove it where it was granted, then run: resolve ID revoked --note ...")


def line(en):
    bits = [en["id"], f"[{en['kind']}/{en['status']}]", en["title"]]
    if en.get("expires"):
        bits.append(f"expires {en['expires']}" + (" EXPIRED" if is_expired(en) else ""))
    if en.get("waiting_on"):
        bits.append(f"waiting on {en['waiting_on']}")
    return "  ".join(bits)


def cmd_list(a):
    for en in fold().values():
        if a.kind and en["kind"] != a.kind:
            continue
        if not a.all and en["status"] not in ("open", "conflict"):
            continue
        print(line(en))


def cmd_show(a):
    entries = fold()
    en = entries[find(entries, a.id)]
    for k, v in en.items():
        if k not in ("history", "heads"):
            print(f"{k}: {v}")
    if en["status"] == "conflict":
        print("CONFLICT: unmerged changes from the same starting point. Values above are NOT trusted.")
    print("history (by parent links, not clock):")
    for e in en["history"]:
        extra = e.get("fields") or e.get("resolution") or e.get("status") or ""
        prev = f" (was {e['previous']})" if e.get("previous") else ""
        why = f" reason: {e['reason']}" if e.get("reason") else ""
        h = " [head]" if e["eid"] in en["heads"] else ""
        print(f"  {e['eid']} {e.get('at','')} {e['op']} {extra}{prev}{why}{h}")


def cmd_check(a):
    """Exit 1 for expired open grants or conflicts."""
    bad = 0
    for i, en in fold().items():
        if en["status"] == "conflict":
            print(f"conflict: {i} {en.get('title','')}"); bad += 1
        elif is_expired(en):
            print(f"expired and still open: {i} {en['title']}"); bad += 1
    sys.exit(1 if bad else 0)


def git(*args, check=True):
    r = subprocess.run(["git", "-C", data_dir(), *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        die(f"git {' '.join(args)} failed: {(r.stderr or r.stdout).strip()}")
    return r


ALLOWED_PATHS = (re.compile(r"^events/[0-9a-f]{12,16}\.json$"), re.compile(r"^pandu\.json$"),
                 re.compile(r"^\.gitignore$"), re.compile(r"^README\.md$"),
                 re.compile(r"^\.github/workflows/sweep\.yml$"))


def path_ok(p):
    return any(r.match(p) for r in ALLOWED_PATHS)


WORKFLOW = ".github/workflows/sweep.yml"
REF_LINE = re.compile(r"(PANDU_REF: )[0-9a-f]{40}$", re.M)


def workflow_problem(text):
    """The workflow holds a write token, so it must be the reviewed template exactly. Only the
    pinned pandu commit hash may differ. Returns a problem string or None."""
    if len(REF_LINE.findall(text)) != 1:
        return "it has no single pinned 40-character pandu commit hash"
    with open(os.path.join(TEMPLATE_DIR, "data-repo", "sweep.yml"), encoding="utf-8") as f:
        want = f.read()
    if REF_LINE.sub(r"\1__PANDU_REF__", text) != want:
        return "it differs from the reviewed template"
    return None


def deny_hits(text):
    return [d for d in config()["deny"] if d and d.lower() in text.lower()]


def check_history(rev, public):
    """Everything reachable from rev must be data-only: allowed paths, events only ever
    added (never edited or removed), and for a public log every historic event blob and
    config blob passes the public rules. Fails closed, so incompatible ancestry is never pushed."""
    r = git("log", "--format=", "--raw", "--no-abbrev", "--no-renames", rev)
    for ln in r.stdout.splitlines():
        if not ln.startswith(":"):
            continue
        meta, _, path = ln.partition("\t")
        status = meta.split()[-1]
        new = meta.split()[3]
        if not path_ok(path):
            die(f"history of {rev} contains unrelated path '{path}'. This repository is not a pandu data-only "
                "repository, so nothing was pushed. Use a fresh repository.")
        if path.startswith("events/") and status != "A":
            die(f"history of {rev} edits or removes event file '{path}'. Nothing was pushed.")
        if path == WORKFLOW:
            if new.strip("0") == "":
                die(f"history of {rev} removes the workflow file. Nothing was pushed.")
            bad = workflow_problem(git("cat-file", "-p", new).stdout)
            if bad:
                die(f"history of {rev} has a workflow that is not the reviewed template: {bad}. Nothing was pushed.")
        if not public or new.strip("0") == "":
            continue
        blob = git("cat-file", "-p", new).stdout
        if not (path.startswith("events/") or path == CONFIG_NAME):
            if deny_hits(blob):  # README.md, .gitignore: no known-private string in any published text
                die(f"history of {rev} has a denied string in '{path}'. Nothing was pushed.")
            continue
        try:
            j = json.loads(blob)
        except ValueError:
            die(f"history of {rev} has an unreadable blob for '{path}'. Nothing was pushed.")
        if path == CONFIG_NAME:
            if "deny" in j:
                die(f"history of {rev} stored private deny strings in {CONFIG_NAME}. Nothing was pushed.")
            continue
        bad = public_problems(j)
        if bad:
            die(f"history of {rev} has an event not allowed in a public log ({path}): " + "; ".join(sorted(set(bad))) +
                ". Nothing was pushed.")


def check_commit_metadata(rev):
    """Author, committer and message text of every reachable commit, for denied strings."""
    meta = git("log", "--format=%an%n%ae%n%cn%n%ce%n%B", rev).stdout
    if deny_hits(meta):
        die(f"commit metadata (author, committer or message) in the history of {rev} contains a denied string. "
            "Nothing was pushed.")


def verify_tree_and_history(public, rev="HEAD"):
    """Full integrity before any commit and before every push."""
    fold()                    # missing parents, cycles, incomplete history, damaged files
    validate_public_events()  # public rules on the working files
    tracked = git("ls-files").stdout.splitlines()
    for p in tracked:
        if not path_ok(p):
            die(f"'{p}' is tracked but is not pandu data. Nothing was pushed.")
    wf = os.path.join(data_dir(), WORKFLOW)
    if os.path.lexists(wf):
        if os.path.islink(wf) or not os.path.isfile(wf):
            die("the workflow file is not a plain file. Nothing was pushed.")
        with open(wf, encoding="utf-8") as f:
            bad = workflow_problem(f.read())
        if bad:
            die(f"the workflow file is not the reviewed template: {bad}. Nothing was pushed.")
    elif WORKFLOW in tracked:
        die("the workflow file was removed. Nothing was pushed.")
    if git("rev-parse", "--verify", "-q", rev, check=False).returncode == 0:
        check_history(rev, public)
        if public:
            check_commit_metadata(rev)


def cmd_sync(a):
    """Commit new events, merge the remote's, push. Only events/ and pandu.json are ever
    committed. Integrity (full event graph, data-only history, public rules) is checked before
    the local commit and again after the merge, before every push. A same-named file with different
    content is the only possible git conflict: the merge is aborted and nothing is overwritten."""
    if git("rev-parse", "--git-dir", check=False).returncode != 0:
        die("the data directory is not a git repository")
    public = config()["visibility"] == "public"
    if not public:
        die("sync only works for a PUBLIC log (pandu init --visibility public). A private log is never pushed anywhere.")
    events_dir()
    # nothing but pandu data may be staged, and nothing is committed until the graph is valid
    staged = git("diff", "--cached", "--name-only").stdout.splitlines()
    odd = [p for p in staged if not path_ok(p)]
    if odd:
        die(f"unrelated paths are staged ({', '.join(odd[:3])}). Unstage them first. Nothing was committed.")
    fold()
    validate_public_events()
    paths = ["events"] + ([CONFIG_NAME] if os.path.exists(os.path.join(data_dir(), CONFIG_NAME)) else [])
    git("add", "--", *paths)
    if git("diff", "--cached", "--quiet", check=False).returncode != 0:
        git("commit", "-q", "-m", a.message)  # the index holds only the allowed paths, verified above and by add
    branch = git("symbolic-ref", "--short", "HEAD").stdout.strip()
    for attempt in range(1, 6):
        git("fetch", "-q", a.remote)
        ref = f"{a.remote}/{branch}"
        has_remote = git("rev-parse", "--verify", "-q", ref, check=False).returncode == 0
        if has_remote:
            check_history(ref, public)
            if public:
                check_commit_metadata(ref)  # refuse to even merge foreign history that is not pandu data
        if has_remote and git("rev-parse", "--verify", "-q", "HEAD", check=False).returncode != 0:
            git("checkout", "-q", "-B", branch, ref)  # nothing local yet: just take the remote
        elif has_remote:
            m = git("merge", "--no-edit", "-q", "--allow-unrelated-histories", ref, check=False)
            if m.returncode != 0:
                git("merge", "--abort", check=False)
                die("merge conflict (two different files with the same name). Merge aborted, nothing overwritten. "
                    + (m.stdout + m.stderr).strip())
        if git("rev-parse", "--verify", "-q", "HEAD", check=False).returncode != 0:
            print("nothing to sync yet"); return
        verify_tree_and_history(public)  # after the merge and before the push
        if git("push", "-q", a.remote, f"HEAD:{branch}", check=False).returncode == 0:
            print(f"synced (attempt {attempt})")
            return
    die("push kept being rejected after 5 attempts; try again")


# ---- scaffold a public data repository (files only, nothing is committed or pushed) ----
SCAFFOLD = (("README.md", "README.md"), ("pandu.json", "pandu.json"), ("gitignore", ".gitignore"),
            ("sweep.yml", ".github/workflows/sweep.yml"))


def cmd_scaffold(a):
    if not re.match(r"^[0-9a-f]{40}$", a.pandu_ref):
        die("--pandu-ref must be the full 40-character commit hash of reviewed pandu code")
    d = a.dir
    if os.path.islink(d):
        die(f"{d} is a symlink; nothing was written")
    if os.path.lexists(d):
        if not os.path.isdir(d):
            die(f"{d} is not a directory; nothing was written")
        extra = [n for n in os.listdir(d) if n != ".git"]
        if extra:
            die(f"{d} is not empty (found {extra[0]}); use an empty directory. Nothing was written")
        g = os.path.join(d, ".git")
        if os.path.lexists(g) and (os.path.islink(g) or not os.path.isdir(g)):
            die(f"{g} is not a plain directory; nothing was written")
    src = os.path.join(TEMPLATE_DIR, "data-repo")
    staged = []  # read and build every file first, so a failure writes nothing
    for name, dest in SCAFFOLD:
        with open(os.path.join(src, name), encoding="utf-8") as f:
            staged.append((os.path.join(d, dest), f.read().replace("__PANDU_REF__", a.pandu_ref)))
    done = []
    try:
        for p, text in staged:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o644)
            done.append(p)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
    except OSError as e:
        for p in done:
            os.remove(p)
        die(f"could not write the files ({e}); the partial files were removed")
    for p, _ in staged:
        print("wrote " + p)


# ---- outbox: plain-text messages about changes, for a private channel ----
SENT_NAME = "sent.txt"


def sent_ids():
    p = os.path.join(data_dir(), SENT_NAME)
    if not os.path.exists(p):
        return set()
    with open(p, encoding="utf-8") as f:
        return {l.strip() for l in f if l.strip()}


def mark_sent(ids):
    p = os.path.join(data_dir(), SENT_NAME)
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as f:
        for i in sorted(ids):
            f.write(i + "\n")


def event_message(e, en):
    t = en.get("title", e["entry"])
    ref = f"(ref {e['entry']})"
    if e["op"] == "add":
        f = e["fields"]
        head = {"approval": "Needs your approval", "waiting": "Waiting", "agreed": "Agreed",
                "work": "Work"}[f["kind"]]
        lines = [f"{head}: {t} {ref}"]
        for k in ("scope", "conditions", "expires", "evidence", "waiting_on", "next_actor"):
            if f.get(k):
                lines.append(f"  {k.replace('_', ' ')}: {f[k]}")
        return "\n".join(lines)
    if e["op"] == "correct":
        ch = "; ".join(f"{k}: {e.get('previous', {}).get(k)} -> {v}" for k, v in e["fields"].items())
        return f"Correction: {t} {ref}\n  {ch}" + (f"\n  reason: {e['reason']}" if e.get("reason") else "")
    if e["op"] == "resolve":
        if e["resolution"] == "expired":
            return (f"Expired: {t} {ref}\n  This only records the expiry. Access was NOT removed. "
                    "Remove it where it was granted, then confirm.")
        return f"{e['resolution'].capitalize()}: {t} {ref}" + (f"\n  note: {e['note']}" if e.get("note") else "")
    return f"Conflict settled as {e['status']}: {t} {ref}" + (f"\n  note: {e['note']}" if e.get("note") else "")


def cmd_outbox(a):
    """Print messages for events not yet reported, plus current attention items.
    This only formats text. It sends nothing, and the log stays the record: a chat
    message is a notification, never the source of truth. After the messages were
    actually delivered, run again with --mark-sent to avoid repeats."""
    entries = fold()
    evs = load_events()
    done = sent_ids()
    pending = sorted((e for e in evs.values() if e["eid"] not in done),
                     key=lambda e: (e.get("at", ""), e["eid"]))
    def full(e):
        t = event_message(e, entries[e["entry"]]) + f"\n  version: {e['eid']}"
        if e.get("parents"):
            t += "\n  replaces: " + ", ".join(e["parents"])
        return t
    msgs = [{"eid": e["eid"], "entry": e["entry"], "text": full(e)} for e in pending]
    attention = []
    for i, en in entries.items():
        if en["status"] == "conflict":
            attention.append(f"CONFLICT: {en.get('title', i)} (ref {i}) changed in parallel; not trusted until settled.")
        elif is_expired(en):
            attention.append(f"EXPIRED but still open: {en['title']} (ref {i}). Run sweep.")
    if a.mark_sent:
        mark_sent([m["eid"] for m in msgs])
        print(f"marked {len(msgs)} message(s) as delivered")
        return
    if a.format == "json":
        print(json.dumps({"messages": msgs, "attention": attention}, indent=1))
    else:
        for m in msgs:
            print(m["text"] + "\n---")
        for x in attention:
            print(x)
        if not msgs and not attention:
            print("nothing to report")


def cmd_due(a):
    """List the expiry notices that are due, with stable idempotency keys. Read-only: it sends
    nothing and writes nothing. A scheduler or a person delivers each key once and keeps its own
    record of what was delivered. The log is an index; the original grant stays the authority."""
    today = today_date()
    out = []
    for i, en in fold().items():
        d = parse_date(en.get("expires"))
        if not d or en["status"] not in ("open", "expired") or en.get("kind") != "agreed":
            continue
        days = (d - today).days
        if days < 0:
            phase = "expired"
        elif days == 0:
            phase = "due"
        elif days <= a.within:
            phase = "upcoming"
        else:
            continue
        title = en.get("title", i)
        text = {"expired": f"Grant expired on {d}: {title} (ref {i}). The log records this only; check that access is really removed.",
                "due": f"Grant expires today: {title} (ref {i}).",
                "upcoming": f"Grant expires in {days} day(s), on {d}: {title} (ref {i})."}[phase]
        # the key names the entry, the expiry date and the phase, so a correction that moves the
        # date gives a new key and a repeat run gives the same key
        out.append({"key": f"{i}:{d}:{phase}", "entry": i, "phase": phase, "expires": str(d), "text": text})
    out.sort(key=lambda x: (x["expires"], x["key"]))
    if a.format == "json":
        print(json.dumps({"today": str(today), "notices": out}, indent=1))
    else:
        for x in out:
            print(f"{x['key']}\t{x['text']}")
        if not out:
            print("nothing due")


# ---- status page ----
def sections(entries):
    vals = list(entries.values())
    op = [e for e in vals if e["status"] == "open"]
    conf = [e for e in vals if e["status"] == "conflict"]
    exp = [e for e in vals if e["kind"] == "agreed" and e["status"] == "expired"]
    fin = [e for e in vals if e["kind"] == "work" and (e.get("state") == "done" or e["status"] == "done")]
    return {
        "Needs attention: conflicting changes (not trusted)": conf,
        "Needs attention: expired grants still open": [e for e in op if is_expired(e)],
        "Running": [e for e in op if e["kind"] == "work" and e.get("state", "running") == "running"],
        "Blocked": [e for e in op if e["kind"] == "waiting" or (e["kind"] == "work" and e.get("state") == "blocked")],
        "Needs approval": [e for e in op if e["kind"] == "approval"],
        "Agreed (active)": [e for e in op if e["kind"] == "agreed" and not is_expired(e)],
        "Expired: access removal not confirmed": exp,
        "Finished work": fin,
        "Closed (not work finished)": [e for e in vals if e["status"] not in ("open", "conflict") and e not in fin and e not in exp],
    }


def next_actor(e):
    if e["kind"] == "approval":
        return "owner"
    if e["kind"] == "waiting":
        return e.get("waiting_on", "unspecified")
    if e["kind"] == "work":
        return e.get("next_actor") or "unspecified"
    return ""


def item_parts(name, e):
    """Plain-text (label, value) pairs shown for one entry."""
    p = []
    if name.startswith("Needs attention: conflicting"):
        p.append(("problem", "changed in parallel from the same starting point; run show, then settle"))
    if name.startswith(("Closed", "Expired")):
        p.append(("outcome", f"{e['kind']} {e['status']}" + (f": {e['resolution_note']}" if e.get("resolution_note") else "")))
    if e["kind"] == "work" and name in ("Running", "Blocked"):
        p.append(("next", next_actor(e)))
    elif e["kind"] in ("approval", "waiting") and e["status"] == "open":
        p.append(("next", next_actor(e)))
    for k, lab in (("scope", "scope"), ("conditions", "conditions")):
        if e.get(k):
            p.append((lab, e[k]))
    if e.get("expires"):
        p.append(("expires", e["expires"] + (" EXPIRED" if is_expired(e) else "")))
    if e.get("evidence"):
        p.append(("evidence", e["evidence"]))
    return p


BRIEF_NOTE = ("BRIEF SUMMARY: scope, conditions and evidence are hidden. A grant listed here is not "
              "unconditional. Open the full view before relying on any grant.")

NOTE = ("This page is an index of a local log, a snapshot of when it was made. "
        "It does not enforce or revoke anything. The linked evidence wins if they disagree.")


BRIEF_KEEP = ("next", "expires", "outcome", "problem")


def shown(entries, brief):
    """Sections to show. The brief view drops empty sections, Finished work and
    Closed, and keeps only action-relevant lines. The full record is unchanged."""
    out = {}
    for name, items in sections(entries).items():
        if brief and (not items or name.startswith(("Finished", "Closed"))):
            continue
        out[name] = items
    return out


def parts_for(name, e, brief):
    ps = item_parts(name, e)
    return [p for p in ps if p[0] in BRIEF_KEEP] if brief else ps


def render_md(entries, brief=False):
    out = ["# Status" + (" (brief summary)" if brief else ""), "", f"Updated {now()}", ""]
    if brief:
        out += [BRIEF_NOTE, ""]
    for name, items in shown(entries, brief).items():
        out.append(f"## {name}")
        if not items:
            out.append("- nothing")
        for e in items:
            out.append(f"- {e['title']}")
            for lab, v in parts_for(name, e, brief):
                out.append(f"  - {lab}: {v}")
        out.append("")
    out.append(NOTE)
    return "\n".join(out) + "\n"


def render_html(entries, brief=False):
    h = html.escape
    parts = ["<!doctype html><html lang=en><meta charset=utf-8>",
             "<meta name=viewport content='width=device-width,initial-scale=1'>",
             "<title>Status</title><style>body{font:16px/1.5 system-ui,sans-serif;max-width:42rem;margin:2rem auto;padding:0 1rem;color:#1b1b1b}"
             "h2{margin-top:1.6rem;border-bottom:1px solid #ccc}li{margin:.4rem 0}.n{color:#555;display:block;font-size:.9em}.x{color:#a00;font-weight:600}</style>",
             f"<h1>Status{' (brief summary)' if brief else ''}</h1><p class=n>Updated {h(now())}</p>"]
    if brief:
        parts.append(f"<p class=x>{h(BRIEF_NOTE)}</p>")
    for name, items in shown(entries, brief).items():
        cls = " class=x" if name.startswith(("Needs attention", "Expired")) and items else ""
        parts.append(f"<h2{cls}>{h(name)}</h2><ul>")
        if not items:
            parts.append("<li class=n>nothing</li>")
        for e in items:
            s = h(e["title"])
            for lab, v in parts_for(name, e, brief):
                c = "n x" if v.endswith("EXPIRED") else "n"
                s += f"<span class='{c}'>{h(lab)}: {h(v)}</span>"
            parts.append(f"<li>{s}</li>")
        parts.append("</ul>")
    parts.append(f"<p class=n>{h(NOTE)}</p></html>")
    return "\n".join(parts) + "\n"


def cmd_status(a):
    entries = fold()
    brief = a.view == "brief"
    out = render_html(entries, brief) if a.format == "html" else render_md(entries, brief)
    if a.out:
        fd = os.open(a.out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"wrote {a.out}")
    else:
        sys.stdout.write(out)


# ---- templates ----
def load_templates():
    t = {}
    if os.path.isdir(TEMPLATE_DIR):
        for fn in sorted(os.listdir(TEMPLATE_DIR)):
            if fn.endswith(".json"):
                with open(os.path.join(TEMPLATE_DIR, fn), encoding="utf-8") as f:
                    t[fn[:-5]] = json.load(f)
    return t


class _Strict(dict):
    def __missing__(self, k):
        sys.exit(f"error: template needs --set {k}=VALUE")


def cmd_templates(a):
    for n, t in load_templates().items():
        print(f"{n}: {t['description']}  (needs: {', '.join(t['fields'])})")


def cmd_grant(a):
    t = load_templates().get(a.template)
    if not t:
        sys.exit(f"error: unknown template '{a.template}' (see: templates)")
    vals = _Strict()
    for s in a.set or []:
        k, _, v = s.partition("=")
        if not v:
            sys.exit(f"error: --set expects KEY=VALUE, got '{s}'")
        vals[k] = v
    f = {"kind": "agreed", "title": t["title"].format_map(vals),
         "scope": t["scope"].format_map(vals),
         "conditions": t["conditions"].format_map(vals),
         "expires": a.expires, "evidence": a.evidence}
    if not f["evidence"]:
        sys.exit("error: --evidence is required: point to where the owner actually agreed")
    if not f["expires"]:
        sys.exit("error: --expires YYYY-MM-DD is required for grants")
    parse_date(f["expires"])
    public_gate(a, f)
    print(new_entry(f, {"template": a.template}))


def main(argv=None):
    p = argparse.ArgumentParser(prog="pandu", description=__doc__.split("\n")[0])
    sp = p.add_subparsers(dest="cmd", required=True)

    def common(x, req_title=True):
        if req_title:
            x.add_argument("title")
        x.add_argument("--scope"); x.add_argument("--conditions"); x.add_argument("--expires")
        x.add_argument("--evidence"); x.add_argument("--waiting-on", dest="waiting_on")
        x.add_argument("--next-actor", dest="next_actor"); x.add_argument("--state")
        x.add_argument("--notes")
        x.add_argument("--public-ok", action="store_true", help="confirm text is fit for a public log")

    x = sp.add_parser("add", help="add an entry"); x.add_argument("kind", choices=KINDS); common(x); x.set_defaults(f=cmd_add)
    x = sp.add_parser("correct", help="correct an entry, keeping history"); x.add_argument("id")
    x.add_argument("--title"); common(x, False); x.add_argument("--reason"); x.set_defaults(f=cmd_correct)
    x = sp.add_parser("resolve", help="close an entry (never deletes)"); x.add_argument("id")
    x.add_argument("resolution", choices=RESOLUTIONS); x.add_argument("--note")
    x.add_argument("--public-ok", action="store_true"); x.set_defaults(f=cmd_resolve)
    x = sp.add_parser("outbox", help="format unreported changes as plain-text messages (sends nothing)")
    x.add_argument("--format", choices=("text", "json"), default="text")
    x.add_argument("--mark-sent", action="store_true", help="after delivery, record these as reported"); x.set_defaults(f=cmd_outbox)
    x = sp.add_parser("due", help="list expiry notices that are due, with idempotency keys (read-only)")
    x.add_argument("--format", choices=("text", "json"), default="text")
    x.add_argument("--within", type=int, default=0, help="also list grants expiring within this many days"); x.set_defaults(f=cmd_due)
    x = sp.add_parser("scaffold", help="write the files for a public data repository (commits nothing)")
    x.add_argument("dir"); x.add_argument("--pandu-ref", required=True, dest="pandu_ref"); x.set_defaults(f=cmd_scaffold)
    x = sp.add_parser("init", help="set this log's visibility (default is private)")
    x.add_argument("--visibility", choices=("public", "private"), required=True)
    x.add_argument("--deny", action="append", help="text that must never appear in a public log, e.g. the private repo's name")
    x.add_argument("--force", action="store_true"); x.set_defaults(f=cmd_init)
    x = sp.add_parser("settle", help="explicitly resolve a conflict"); x.add_argument("id")
    x.add_argument("status", choices=("open",) + RESOLUTIONS); x.add_argument("--title"); common(x, False)
    x.add_argument("--note"); x.set_defaults(f=cmd_settle)
    x = sp.add_parser("sync", help="commit, merge and push events in a git data repo"); x.add_argument("--remote", default="origin")
    x.add_argument("--message", default="pandu: record events"); x.set_defaults(f=cmd_sync)
    x = sp.add_parser("sweep", help="record expired grants as expired"); x.add_argument("--dry-run", action="store_true"); x.set_defaults(f=cmd_sweep)
    x = sp.add_parser("list"); x.add_argument("--kind", choices=KINDS); x.add_argument("--all", action="store_true"); x.set_defaults(f=cmd_list)
    x = sp.add_parser("show"); x.add_argument("id"); x.set_defaults(f=cmd_show)
    x = sp.add_parser("check", help="exit 1 if expired grants are still open"); x.set_defaults(f=cmd_check)
    x = sp.add_parser("status", help="render the status page"); x.add_argument("--format", choices=("md", "html"), default="md")
    x.add_argument("--view", choices=("full", "brief"), default="full",
                   help="brief: only sections with items that need action; full: everything")
    x.add_argument("--out"); x.set_defaults(f=cmd_status)
    x = sp.add_parser("templates", help="list grant templates"); x.set_defaults(f=cmd_templates)
    x = sp.add_parser("grant", help="record a grant from a template"); x.add_argument("template")
    x.add_argument("--set", action="append"); x.add_argument("--expires"); x.add_argument("--evidence")
    x.add_argument("--public-ok", action="store_true"); x.set_defaults(f=cmd_grant)
    a = p.parse_args(argv)
    a.f(a)


if __name__ == "__main__":
    main()
