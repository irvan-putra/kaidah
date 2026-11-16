import contextlib, io, os, re, subprocess, sys, tempfile, unittest, shutil, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import pandu

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "tools", "pandu.py")


def run(*args):
    out = io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out):
        try:
            pandu.main(list(args))
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 2
            if isinstance(e.code, str):
                out.write(e.code)
    return code, out.getvalue()


def section(s, name):
    a = s.index("## " + name)
    n = s.find("\n## ", a + 3)
    return s[a:n if n != -1 else len(s)]


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.old = dict(os.environ)
        os.environ["PANDU_DIR"] = self.d.name
        os.environ.pop("PANDU_TODAY", None); os.environ.pop("PANDU_TEST_MODE", None)

    def tearDown(self):
        os.environ.clear(); os.environ.update(self.old)
        self.d.cleanup()

    def add(self, *a):
        c, o = run("add", *a)
        self.assertEqual(c, 0, o)
        return o.strip()


class Basics(Base):
    def test_agreed_needs_evidence(self):
        self.assertNotEqual(run("add", "agreed", "x")[0], 0)

    def test_correct_keeps_history(self):
        i = self.add("agreed", "Push", "--evidence", "m", "--expires", "2099-01-01")
        run("correct", i, "--expires", "2099-06-01", "--reason", "extended")
        _, s = run("show", i)
        self.assertIn("2099-06-01", s); self.assertIn("2099-01-01", s); self.assertIn("extended", s)

    def test_closed_is_never_reopened_by_edit(self):
        i = self.add("agreed", "G", "--evidence", "m", "--expires", "2099-01-01")
        run("resolve", i, "revoked")
        c, o = run("correct", i, "--expires", "2099-12-31")
        self.assertNotEqual(c, 0); self.assertIn("never reopened", o)
        self.assertEqual(run("resolve", i, "approved")[0], 2)

    def test_status_sections(self):
        self.add("work", "Build thing", "--next-actor", "assistant")
        self.add("work", "No owner")
        self.add("waiting", "Need DNS", "--waiting-on", "owner")
        self.add("approval", "Publish page")
        _, s = run("status")
        self.assertIn("- Build thing\n  - next: assistant", section(s, "Running"))
        self.assertIn("next: unspecified", section(s, "Running"))
        self.assertIn("- Need DNS\n  - next: owner", s)
        self.assertIn("- Publish page\n  - next: owner", s)

    def test_html_escapes(self):
        self.add("work", "<script>x</script>")
        _, s = run("status", "--format", "html")
        self.assertNotIn("<script>x", s); self.assertIn("&lt;script&gt;", s)

    def test_grant_template_and_scope_visible(self):
        _, i = run("grant", "push-access", "--set", "repo=demo", "--set", "project=docs",
                   "--expires", "2099-01-01", "--evidence", "m")
        _, s = run("status")
        a = section(s, "Agreed")
        self.assertIn("Push access to demo for docs", a)
        self.assertIn("scope: Push commits to demo", a); self.assertIn("conditions: Public, generic", a)
        self.assertNotEqual(run("grant", "push-access", "--set", "repo=demo", "--expires", "2099-01-01", "--evidence", "m")[0], 0)
        self.assertNotEqual(run("grant", "push-access", "--set", "repo=a", "--set", "project=b", "--evidence", "m")[0], 0)

    def test_closed_outcomes_visible(self):
        for kind, res in (("approval", "approved"), ("approval", "denied"), ("agreed", "revoked"), ("agreed", "archived")):
            i = self.add(kind, f"{res} thing", "--evidence", "m")
            run("resolve", i, res, "--note", "n-" + res)
        _, s = run("status")
        c = section(s, "Closed")
        for res in ("approved", "denied", "revoked", "archived"):
            self.assertIn(f"{res} thing", c); self.assertIn(f"{res}: n-{res}", c)
        self.assertNotIn("approved thing", section(s, "Finished work"))

    def test_work_done_is_finished_work(self):
        i = self.add("work", "Ship", "--next-actor", "a"); run("resolve", i, "done")
        self.add("work", "Ship2", "--state", "done")
        _, s = run("status")
        self.assertIn("Ship2", section(s, "Finished work")); self.assertIn("Ship", section(s, "Finished work"))
        self.assertNotIn("Ship", section(s, "Closed"))

    def test_brief_view_is_short_and_full_view_unchanged(self):
        self.add("work", "Doing", "--next-actor", "assistant")
        i = self.add("agreed", "Old", "--evidence", "e", "--scope", "sc", "--conditions", "co", "--expires", "2000-01-01")
        j = self.add("work", "Shipped"); run("resolve", j, "done")
        _, b = run("status", "--view", "brief")
        self.assertIn("Doing", b); self.assertIn("Needs attention: expired", b)
        self.assertNotIn("scope:", b); self.assertNotIn("evidence:", b)
        self.assertNotIn("Shipped", b); self.assertNotIn("nothing", b)
        self.assertIn("expires: 2000-01-01 EXPIRED", b)
        self.assertIn("BRIEF SUMMARY", b); self.assertIn("not unconditional", b)
        _, bh = run("status", "--view", "brief", "--format", "html")
        self.assertIn("BRIEF SUMMARY", bh)
        _, f = run("status")
        self.assertNotIn("BRIEF SUMMARY", f)
        self.assertIn("scope: sc", f); self.assertIn("Shipped", f); self.assertIn("evidence: e", f)

    def test_permissions(self):
        self.add("work", "x")
        out = os.path.join(self.d.name, "s.md")
        run("status", "--out", out)
        ev = os.path.join(self.d.name, "events")
        f = os.path.join(ev, os.listdir(ev)[0])
        self.assertEqual(os.stat(f).st_mode & 0o777, 0o600)
        self.assertEqual(os.stat(out).st_mode & 0o777, 0o600)
        self.assertEqual(os.stat(ev).st_mode & 0o777, 0o700)


class Expiry(Base):
    def test_test_date_override_refused_without_test_mode(self):
        os.environ["PANDU_TODAY"] = "2030-01-01"
        c, o = run("list")  # reading is fine
        self.add("agreed", "G", "--evidence", "m", "--expires", "2029-12-31")
        c, o = run("sweep")
        self.assertNotEqual(c, 0); self.assertIn("test-only", o)
        c, o = run("status"); self.assertNotEqual(c, 0)

    def test_expired_open_not_active_and_sweep_not_revocation(self):
        i = self.add("agreed", "Old", "--evidence", "m", "--expires", "2000-01-01")
        _, s = run("status")
        self.assertIn("Old", section(s, "Needs attention: expired"))
        self.assertNotIn("Old", section(s, "Agreed (active)"))
        self.assertEqual(run("check")[0], 1)
        _, o = run("sweep"); self.assertIn("does not remove any access", o)
        _, s = run("status")
        self.assertIn("Old", section(s, "Expired: access removal not confirmed"))
        self.assertNotIn("Old", section(s, "Closed"))
        self.assertEqual(run("check")[0], 0)
        run("resolve", i, "revoked", "--note", "removed in settings")
        _, s = run("status")
        self.assertNotIn("Old", section(s, "Expired"))
        self.assertIn("revoked: removed in settings", section(s, "Closed"))

    def test_sweep_is_idempotent_and_deterministic(self):
        os.environ["PANDU_TEST_MODE"] = "1"; os.environ["PANDU_TODAY"] = "2030-01-01"
        self.add("agreed", "G", "--evidence", "m", "--expires", "2029-12-31")
        run("sweep"); n = len(os.listdir(os.path.join(self.d.name, "events")))
        run("sweep")
        self.assertEqual(len(os.listdir(os.path.join(self.d.name, "events"))), n)


class Outbox(Base):
    def test_messages_cover_add_correct_expiry_and_mark_sent(self):
        i = self.add("agreed", "Push access", "--evidence", "ev", "--scope", "repo X", "--expires", "2000-01-01")
        run("correct", i, "--scope", "repo Y", "--reason", "narrowed")
        a = self.add("approval", "Publish draft")
        run("sweep")
        c, o = run("outbox")
        self.assertEqual(c, 0)
        self.assertIn("Agreed: Push access", o); self.assertIn("scope: repo X", o)
        self.assertIn("Correction: Push access", o); self.assertIn("repo X -> repo Y", o); self.assertIn("reason: narrowed", o)
        self.assertIn("Needs your approval: Publish draft", o)
        self.assertIn("Access was NOT removed", o)
        self.assertIn("version: ", o); self.assertIn("replaces: ", o)
        run("outbox", "--mark-sent")
        _, o = run("outbox"); self.assertIn("nothing to report", o)
        run("resolve", i, "revoked", "--note", "done in settings")
        _, o = run("outbox"); self.assertIn("Revoked: Push access", o); self.assertNotIn("Agreed:", o)

    def test_attention_items_repeat_until_fixed_and_json_valid(self):
        self.add("agreed", "G", "--evidence", "e", "--expires", "2000-01-01")
        run("outbox", "--mark-sent")
        _, o = run("outbox", "--format", "json")
        d = json.loads(o)
        self.assertEqual(d["messages"], []); self.assertIn("EXPIRED but still open", d["attention"][0])

    def test_outbox_is_read_only_for_the_log_and_private(self):
        self.add("work", "x")
        n = len(os.listdir(os.path.join(self.d.name, "events")))
        run("outbox"); run("outbox", "--mark-sent")
        self.assertEqual(len(os.listdir(os.path.join(self.d.name, "events"))), n)
        self.assertEqual(os.stat(os.path.join(self.d.name, "sent.txt")).st_mode & 0o777, 0o600)


class Due(Base):
    def test_due_notices_are_stable_read_only_and_follow_corrections(self):
        os.environ["PANDU_TEST_MODE"] = "1"; os.environ["PANDU_TODAY"] = "2026-06-10"
        a = self.add("agreed", "Grant A", "--evidence", "x", "--expires", "2026-06-10")
        b = self.add("agreed", "Grant B", "--evidence", "x", "--expires", "2026-06-12")
        self.add("agreed", "No expiry", "--evidence", "x")
        self.add("work", "Not a grant")
        n = len(os.listdir(os.path.join(self.d.name, "events")))
        def due(*x):
            c, o = run("due", "--format", "json", *x); self.assertEqual(c, 0, o); return json.loads(o)["notices"]
        d1 = due()
        self.assertEqual([(x["entry"], x["phase"]) for x in d1], [(a, "due")])
        self.assertEqual(due(), d1)  # same input, same keys
        up = due("--within", "3")
        self.assertEqual([x["phase"] for x in up], ["due", "upcoming"])
        self.assertEqual(len(os.listdir(os.path.join(self.d.name, "events"))), n)  # writes nothing
        run("correct", b, "--expires", "2026-06-20")
        self.assertEqual(len(due("--within", "3")), 1)
        os.environ["PANDU_TODAY"] = "2026-06-11"
        e1 = due(); self.assertEqual([(x["entry"], x["phase"]) for x in e1], [(a, "expired")])
        run("sweep")  # sweeping must not drop or change the notice
        self.assertEqual(due(), e1)
        run("resolve", a, "revoked")  # an explicitly closed grant is no longer due
        self.assertEqual(due(), [])
        c, o = run("due"); self.assertEqual(o.strip(), "nothing due")


class DueSent(Base):
    def setUp(self):
        super().setUp()
        os.environ["PANDU_TEST_MODE"] = "1"; os.environ["PANDU_TODAY"] = "2026-06-10"
        self.a = self.add("agreed", "Grant A", "--evidence", "x", "--expires", "2026-06-10")
        self.b = self.add("agreed", "Grant B", "--evidence", "x", "--expires", "2026-06-01")
        self.f = os.path.join(self.d.name, "..", "sentfile-" + os.path.basename(self.d.name) + ".txt")
        self.f = os.path.abspath(self.f)
        self.addCleanup(lambda: os.path.exists(self.f) and os.remove(self.f))

    def due(self, *x):
        c, o = run("due", "--format", "json", "--sent-file", self.f, *x); self.assertEqual(c, 0, o)
        return json.loads(o)["notices"]

    def test_marking_hides_only_that_key_and_is_idempotent(self):
        n = self.due(); self.assertEqual(len(n), 2)
        self.assertIn(n[0]["key"], n[0]["message"])  # the message carries its key
        self.assertFalse(os.path.exists(self.f))  # listing writes nothing
        k = n[0]["key"]
        c, o = run("due", "--sent-file", self.f, "--mark-sent", k); self.assertEqual(c, 0); self.assertIn("recorded 1", o)
        self.assertEqual([x["key"] for x in self.due()], [n[1]["key"]])
        c, o = run("due", "--sent-file", self.f, "--mark-sent", k); self.assertIn("1 unchanged", o)
        with open(self.f) as fh:
            self.assertEqual(fh.read(), k + "\n")  # no duplicate line
        self.assertEqual(os.stat(self.f).st_mode & 0o777, 0o600)
        # listing alone never marks: the other notice is still pending after a re-run
        self.assertEqual(len(self.due()), 1); self.assertEqual(len(self.due()), 1)

    def test_attempt_states_pause_a_notice_until_resolved(self):
        k = self.due()[0]["key"]
        def st():
            c, o = run("due", "--format", "json", "--sent-file", self.f); d = json.loads(o)
            return [x["key"] for x in d["notices"]], [x["key"] for x in d["uncertain"]]
        self.assertIn(k, st()[0])
        run("due", "--sent-file", self.f, "--mark-attempt", k)
        pend, unc = st(); self.assertNotIn(k, pend); self.assertEqual(unc, [k])  # never resent while unknown
        self.assertIn("UNCERTAIN", run("due", "--sent-file", self.f)[1])
        run("due", "--sent-file", self.f, "--mark-attempt", k)  # repeat adds no line
        with open(self.f) as fh:
            self.assertEqual(fh.read(), "?" + k + "\n")
        run("due", "--sent-file", self.f, "--clear-attempt", k)  # confirmed not delivered: pending again
        pend, unc = st(); self.assertIn(k, pend); self.assertEqual(unc, [])
        run("due", "--sent-file", self.f, "--mark-attempt", k); run("due", "--sent-file", self.f, "--mark-sent", k)
        pend, unc = st(); self.assertNotIn(k, pend); self.assertEqual(unc, [])  # delivered wins
        c, o = run("due", "--sent-file", self.f, "--clear-attempt", k); self.assertNotEqual(c, 0)  # cannot undo delivered
        c, o = run("due", "--sent-file", self.f, "--mark-attempt", k); self.assertEqual(c, 0); self.assertIn("unchanged", o)
        c, o = run("due", "--sent-file", self.f, "--mark-sent", k, "--mark-attempt", k); self.assertNotEqual(c, 0)

    def test_a_corrected_date_is_a_new_notice(self):
        k = self.due()[0]["key"]; run("due", "--sent-file", self.f, "--mark-sent", k)
        run("correct", self.a, "--expires", "2026-06-11"); run("correct", self.b, "--expires", "2026-06-20")
        os.environ["PANDU_TODAY"] = "2026-06-11"
        keys = [x["key"] for x in self.due()]
        self.assertEqual(keys, [f"{self.a}:2026-06-11:due"])

    def test_bad_files_and_keys_fail_closed(self):
        for text in ("garbage\n", self.a + ":2026-06-10:due", "\xff\n"):
            with open(self.f, "wb") as fh:
                fh.write(text.encode("latin-1"))
            c, o = run("due", "--sent-file", self.f); self.assertNotEqual(c, 0, text)
            c, o = run("due", "--sent-file", self.f, "--mark-sent", f"{self.a}:2026-06-10:due"); self.assertNotEqual(c, 0, text)
            with open(self.f, "rb") as fh:
                self.assertEqual(fh.read(), text.encode("latin-1"))  # not changed
        os.remove(self.f)
        c, o = run("due", "--sent-file", self.f, "--mark-sent", "not-a-key"); self.assertNotEqual(c, 0)
        self.assertFalse(os.path.exists(self.f))
        self.assertNotEqual(run("due", "--mark-sent", f"{self.a}:2026-06-10:due")[0], 0)  # needs --sent-file

    def test_symlink_is_refused(self):
        target = self.f + ".target"
        with open(target, "w") as fh:
            fh.write("")
        self.addCleanup(os.remove, target)
        os.symlink(target, self.f)
        self.assertNotEqual(run("due", "--sent-file", self.f)[0], 0)
        self.assertNotEqual(run("due", "--sent-file", self.f, "--mark-sent", f"{self.a}:2026-06-10:due")[0], 0)

    def test_parallel_marks_do_not_duplicate_or_lose_keys(self):
        import threading
        keys = [f"{self.a}:2026-06-{d:02d}:due" for d in range(1, 21)]
        errs = []
        def go(chunk):
            try:
                pandu.append_sent_keys(self.f, chunk)
            except BaseException as e:
                errs.append(e)
        ts = [threading.Thread(target=go, args=(keys[i::4] + keys[:3],)) for i in range(4)]
        for t in ts: t.start()
        for t in ts: t.join()
        self.assertEqual(errs, [])
        with open(self.f) as fh:
            lines = fh.read().split("\n")[:-1]
        self.assertEqual(sorted(lines), sorted(keys))


class Checkpoint(Base):
    def setUp(self):
        super().setUp()
        os.environ["PANDU_TEST_MODE"] = "1"; os.environ["PANDU_TODAY"] = "2026-06-10"
        self.a = self.add("agreed", "Synthetic grant", "--evidence", "example reference", "--expires", "2026-06-10")
        run("correct", self.a, "--expires", "2026-06-11")
        self.base = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.base, True)
        self.sent = os.path.join(self.base, "sent.txt"); self.cp = os.path.join(self.base, "cp.json")
        self.key = f"{self.a}:2026-06-11:due"
        run("due", "--sent-file", self.sent, "--mark-attempt", self.key)

    def test_round_trip_keeps_events_and_uncertain_state(self):
        c, o = run("checkpoint", "export", self.cp, "--sent-file", self.sent); self.assertEqual(c, 0, o)
        self.assertEqual(os.stat(self.cp).st_mode & 0o777, 0o600)
        self.assertNotEqual(run("checkpoint", "export", self.cp)[0], 0)  # never overwrites
        c, o = run("checkpoint", "verify", self.cp); self.assertEqual(c, 0); self.assertIn("1 uncertain", o)
        new = os.path.join(self.base, "restored"); sent2 = os.path.join(self.base, "sent2.txt")
        c, o = run("checkpoint", "restore", self.cp, "--into", new, "--sent-file", sent2); self.assertEqual(c, 0, o)
        os.environ["PANDU_DIR"] = new
        self.assertEqual(fold_status(self.a), "open")
        os.environ["PANDU_TODAY"] = "2026-06-11"
        c, o = run("due", "--format", "json", "--sent-file", sent2)
        self.assertEqual([x["key"] for x in json.loads(o)["uncertain"]], [self.key])  # still not resent after restore
        with open(self.sent) as f1, open(sent2) as f2:
            self.assertEqual(f1.read(), f2.read())
        self.assertNotEqual(run("checkpoint", "restore", self.cp, "--into", new)[0], 0)  # not empty

    def test_restore_never_drops_the_sent_record(self):
        run("checkpoint", "export", self.cp, "--sent-file", self.sent)
        new = os.path.join(self.base, "r2")
        c, o = run("checkpoint", "restore", self.cp, "--into", new); self.assertNotEqual(c, 0); self.assertIn("--sent-file", o)
        self.assertFalse(os.path.exists(new))
        run("checkpoint", "export", os.path.join(self.base, "cp2.json"))  # no sent record at all: restoring without one is fine
        self.assertEqual(run("checkpoint", "restore", os.path.join(self.base, "cp2.json"), "--into", new)[0], 0)

    def test_restore_leaves_nothing_behind_when_publishing_fails(self):
        from unittest import mock
        run("checkpoint", "export", self.cp, "--sent-file", self.sent)
        before = sorted(os.listdir(self.base))
        new = os.path.join(self.base, "r3"); sent2 = os.path.join(self.base, "sent3.txt")
        with mock.patch("os.rename", side_effect=OSError("disk error")):  # fails after the sent record was linked in
            c, o = run("checkpoint", "restore", self.cp, "--into", new, "--sent-file", sent2)
        self.assertNotEqual(c, 0); self.assertIn("nothing was left behind", o)
        self.assertEqual(sorted(os.listdir(self.base)), before)  # no dir, no sent file, no staging or temp files
        with mock.patch("os.link", side_effect=OSError("disk error")):  # fails while publishing the sent record
            c, o = run("checkpoint", "restore", self.cp, "--into", new, "--sent-file", sent2)
        self.assertNotEqual(c, 0); self.assertEqual(sorted(os.listdir(self.base)), before)
        self.assertEqual(run("checkpoint", "restore", self.cp, "--into", new, "--sent-file", sent2)[0], 0)  # clean retry works

    def test_export_sees_a_consistent_pair_while_appends_run(self):
        import threading
        keys = [f"{self.a}:2026-07-{d:02d}:due" for d in range(1, 29)]
        stop = []
        def writer():
            for k in keys:
                pandu.append_sent_keys(self.sent, [k], "attempt")
                pandu.append_sent_keys(self.sent, [k], "sent")
            stop.append(1)
        t = threading.Thread(target=writer); t.start()
        seen = 0
        while not stop or seen < 3:
            ev, sent = pandu.snapshot(self.sent)
            st = pandu.parse_sent_text(sent, "x")  # always whole lines, never a torn write
            self.assertTrue(set(st) <= set(keys) | {self.key})
            seen += 1
            if seen > 5000:
                break
        t.join()
        ev, sent = pandu.snapshot(self.sent)
        st = pandu.parse_sent_text(sent, "x")
        self.assertTrue(all(st[k] == "sent" for k in keys))  # every fsynced mark is in the final export

    def test_covers_gate_before_sending(self):
        run("checkpoint", "export", self.cp, "--sent-file", self.sent)
        c, o = run("checkpoint", "covers", self.cp, "--sent-file", self.sent, "--key", self.key); self.assertEqual(c, 0, o)
        k2 = f"{self.a}:2026-06-11:expired"
        self.assertNotEqual(run("checkpoint", "covers", self.cp, "--sent-file", self.sent, "--key", k2)[0], 0)  # no attempt recorded
        run("due", "--sent-file", self.sent, "--mark-attempt", k2)  # state moved on after publishing
        c, o = run("checkpoint", "covers", self.cp, "--sent-file", self.sent, "--key", self.key)
        self.assertNotEqual(c, 0); self.assertIn("STALE", o)
        run("checkpoint", "export", os.path.join(self.base, "cp3.json"), "--sent-file", self.sent)
        self.assertEqual(run("checkpoint", "covers", os.path.join(self.base, "cp3.json"), "--sent-file", self.sent, "--key", k2)[0], 0)
        self.add("work", "new event")  # a new event makes the old checkpoint stale too
        self.assertNotEqual(run("checkpoint", "covers", os.path.join(self.base, "cp3.json"), "--sent-file", self.sent)[0], 0)

    def test_damaged_or_foreign_checkpoints_fail_closed(self):
        run("checkpoint", "export", self.cp, "--sent-file", self.sent)
        with open(self.cp) as f:
            good = json.load(f)
        def bad(mut):
            c = json.loads(json.dumps(good)); mut(c)
            p = os.path.join(self.base, "bad.json")
            with open(p, "w") as f:
                json.dump(c, f)
            tgt = os.path.join(self.base, "t"); shutil.rmtree(tgt, True)
            self.assertNotEqual(run("checkpoint", "verify", p)[0], 0)
            self.assertNotEqual(run("checkpoint", "restore", p, "--into", tgt)[0], 0)
            self.assertFalse(os.path.exists(tgt))
        bad(lambda c: c.update(format="pandu-checkpoint-2"))
        bad(lambda c: c.update(sent="x\n"))                     # checksum mismatch
        bad(lambda c: c["events"].popitem())                     # checksum mismatch
        bad(lambda c: c.update(extra=1))
        def resum(c):
            c["sent"] = "garbage\n"; c["sha256"] = pandu.checkpoint_digest(c["events"], c["sent"])
        bad(resum)                                                # valid checksum, invalid sent record
        def orphan(c):
            e = next(iter(c["events"].values())); k = "a" * 12
            c["events"][k] = dict(e, eid=k, op="correct", parents=["b" * 12])
            c["sha256"] = pandu.checkpoint_digest(c["events"], c["sent"])
        bad(orphan)                                               # missing parent
        with open(self.cp, "w") as f:
            f.write("{not json")
        self.assertNotEqual(run("checkpoint", "verify", self.cp)[0], 0)


class Visibility(Base):
    def public(self, *deny):
        args = ["init", "--visibility", "public"]
        for d in deny:
            args += ["--deny", d]
        self.assertEqual(run(*args)[0], 0)

    def test_default_is_private_and_unrestricted(self):
        self.assertEqual(run("add", "agreed", "G", "--evidence", "msg from chat")[0], 0)

    def test_public_needs_explicit_ok_and_public_evidence(self):
        self.public()
        c, o = run("add", "work", "Public thing"); self.assertNotEqual(c, 0); self.assertIn("--public-ok", o)
        self.assertEqual(run("add", "work", "Public thing", "--public-ok")[0], 0)
        c, o = run("add", "agreed", "G", "--evidence", "a private chat message", "--public-ok")
        self.assertNotEqual(c, 0); self.assertIn("public http(s) link", o)
        c, o = run("add", "agreed", "G", "--evidence", "/home/me/notes.txt", "--public-ok"); self.assertNotEqual(c, 0)
        self.assertEqual(run("add", "agreed", "G", "--evidence", "https://example.com/decision", "--public-ok")[0], 0)

    def test_deny_list_blocks_private_names_everywhere(self):
        self.public("secret-repo")
        for args in (("add", "work", "see Secret-Repo"), ("add", "work", "x", "--notes", "in secret-repo")):
            c, o = run(*args, "--public-ok"); self.assertNotEqual(c, 0); self.assertIn("denied string", o)
        i = self.add_pub("work", "fine")
        self.assertNotEqual(run("resolve", i, "done", "--note", "see secret-repo", "--public-ok")[0], 0)
        self.assertNotEqual(run("correct", i, "--notes", "secret-repo", "--public-ok")[0], 0)
        self.assertNotEqual(run("resolve", i, "done")[0], 0)  # still needs --public-ok

    def add_pub(self, *a):
        c, o = run("add", *a, "--public-ok"); self.assertEqual(c, 0, o); return o.strip()

    def test_init_cannot_silently_flip_and_deny_accumulates(self):
        self.public("one")
        c, o = run("init", "--visibility", "private"); self.assertNotEqual(c, 0)
        self.public("two")
        self.assertEqual(sorted(pandu.config()["deny"]), ["one", "two"])
        self.assertEqual(run("init", "--visibility", "private", "--force")[0], 0)

    def test_damaged_config_fails_closed(self):
        with open(os.path.join(self.d.name, "pandu.json"), "w") as f:
            f.write("{nope")
        self.assertNotEqual(run("add", "work", "x")[0], 0)

    def test_grant_template_gated_in_public(self):
        self.public()
        a = ("grant", "push-access", "--set", "repo=demo", "--set", "project=docs", "--expires", "2099-01-01")
        self.assertNotEqual(run(*a, "--evidence", "https://example.com/d")[0], 0)
        self.assertEqual(run(*a, "--evidence", "https://example.com/d", "--public-ok")[0], 0)


class Integrity(Base):
    def test_damaged_event_fails_closed(self):
        self.add("work", "ok")
        ev = os.path.join(self.d.name, "events")
        with open(os.path.join(ev, "bad0.json"), "w") as f:
            f.write('{"op": "add", "en')
        for cmd in (("list",), ("status",), ("add", "work", "z")):
            c, o = run(*cmd); self.assertNotEqual(c, 0); self.assertIn("bad0.json", o)
        self.assertEqual(len(os.listdir(ev)), 2)

    def test_filename_must_match_event_id(self):
        self.add("work", "ok")
        ev = os.path.join(self.d.name, "events")
        src = os.path.join(ev, os.listdir(ev)[0])
        shutil.copy(src, os.path.join(ev, "zzzz.json"))
        self.assertNotEqual(run("list")[0], 0)

    def test_missing_parent_or_add_fails_closed(self):
        i = self.add("agreed", "G", "--evidence", "m")
        run("correct", i, "--notes", "n")
        ev = os.path.join(self.d.name, "events")
        os.unlink(os.path.join(ev, i + ".json"))
        c, o = run("list"); self.assertNotEqual(c, 0); self.assertIn("missing", o)

    def test_parallel_adds(self):
        env = dict(os.environ, PANDU_DIR=self.d.name)
        ps = [subprocess.Popen([sys.executable, SCRIPT, "add", "work", f"w{k}-{n}"], env=env, stdout=subprocess.DEVNULL)
              for k in range(8) for n in range(5)]
        for p in ps:
            self.assertEqual(p.wait(), 0)
        self.assertEqual(len(pandu.fold()), 40)

    def edit_in_two_places(self):
        i = self.add("agreed", "G", "--evidence", "m", "--expires", "2000-01-01")
        evd = os.path.join(self.d.name, "events")
        # two writers start from the same state: simulate with a second copy of the dir
        other = tempfile.mkdtemp()
        shutil.copytree(evd, os.path.join(other, "events"))
        run("correct", i, "--expires", "2099-01-01", "--reason", "A extends")
        os.environ["PANDU_DIR"] = other
        run("resolve", i, "revoked", "--note", "B revokes")
        os.environ["PANDU_DIR"] = self.d.name
        for fn in os.listdir(os.path.join(other, "events")):
            dst = os.path.join(evd, fn)
            if not os.path.exists(dst):
                shutil.copy(os.path.join(other, "events", fn), dst)
        shutil.rmtree(other)
        return i

    def test_concurrent_edits_conflict_fail_closed(self):
        i = self.edit_in_two_places()
        _, s = run("status")
        self.assertIn("G", section(s, "Needs attention: conflicting"))
        for name in ("Agreed (active)", "Closed", "Expired", "Needs attention: expired"):
            self.assertNotIn("G", section(s, name))
        self.assertEqual(run("check")[0], 1)
        self.assertNotEqual(run("correct", i, "--notes", "x")[0], 0)
        self.assertNotEqual(run("resolve", i, "approved")[0], 0)
        self.assertEqual(run("sweep")[0], 0)  # never touches a conflicted entry
        self.assertEqual(fold_status(i), "conflict")

    def test_settle_is_explicit_and_merges_both(self):
        i = self.edit_in_two_places()
        self.assertEqual(run("settle", i, "revoked", "--note", "revoke wins")[0], 0)
        self.assertEqual(fold_status(i), "revoked")
        self.assertEqual(run("check")[0], 0)
        # order of display/state never came from clocks
        self.assertEqual(len(pandu.fold()[i]["heads"]), 1)

    def test_clock_skew_cannot_revive_a_grant(self):
        i = self.add("agreed", "G", "--evidence", "m", "--expires", "2099-01-01")
        run("resolve", i, "revoked")
        evd = os.path.join(self.d.name, "events")
        # a stale correct from an older clone, stamped in the far future, same parent as the revoke
        head_add = i
        ev = {"op": "correct", "entry": i, "parents": [head_add], "fields": {"expires": "2100-01-01"},
              "at": "2999-01-01T00:00:00+00:00"}
        pandu.write_event(ev)
        self.assertEqual(fold_status(i), "conflict")


def fold_status(i):
    return pandu.fold()[i]["status"]


class Git(Base):
    def g(self, cwd, *a):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
        r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def setUp(self):
        super().setUp()
        self.t = tempfile.mkdtemp()
        self.bare = os.path.join(self.t, "remote.git")
        self.g(self.t, "init", "-q", "--bare", "-b", "main", self.bare)
        self.A = os.path.join(self.t, "A"); self.B = os.path.join(self.t, "B")
        for p in (self.A, self.B):
            self.g(self.t, "init", "-q", "-b", "main", p)
            self.g(p, "remote", "add", "origin", self.bare)
        for k, v in dict(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
                         GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid").items():
            os.environ[k] = v

    def tearDown(self):
        shutil.rmtree(self.t, ignore_errors=True)
        super().tearDown()

    def tamper(self, p, title):
        with open(p) as f:
            d = json.load(f)
        d["fields"]["title"] = title
        with open(p, "w") as f:
            f.write(json.dumps(d, sort_keys=True, indent=1) + "\n")

    def use(self, p):
        os.environ["PANDU_DIR"] = p
        if not os.path.exists(os.path.join(p, "pandu.json")):
            run("init", "--visibility", "public")

    def add(self, *a):
        c, o = run("add", *a, "--public-ok")
        self.assertEqual(c, 0, o)
        return o.strip()

    def test_two_clones_add_and_sync_without_conflict(self):
        self.use(self.A); self.add("work", "from A"); self.assertEqual(run("sync")[0], 0)
        self.use(self.B); self.add("work", "from B")
        c, o = run("sync"); self.assertEqual(c, 0, o)   # B must merge A's push first
        self.use(self.A); self.assertEqual(run("sync")[0], 0)
        self.assertEqual(sorted(e["title"] for e in pandu.fold().values()), ["from A", "from B"])

    def test_concurrent_edit_through_git_becomes_conflict(self):
        self.use(self.A)
        i = self.add("agreed", "G", "--evidence", "https://example.com/m", "--expires", "2000-01-01"); run("sync")
        self.use(self.B); run("sync")
        self.use(self.A); run("correct", i, "--expires", "2099-01-01", "--public-ok"); self.assertEqual(run("sync")[0], 0)
        self.use(self.B); run("resolve", i, "revoked", "--public-ok"); c, o = run("sync"); self.assertEqual(c, 0, o)
        self.assertEqual(fold_status(i), "conflict")
        self.assertEqual(run("check")[0], 1)

    def test_two_machines_sweep_same_day_do_not_conflict(self):
        os.environ["PANDU_TEST_MODE"] = "1"; os.environ["PANDU_TODAY"] = "2030-01-01"
        self.use(self.A)
        i = self.add("agreed", "G", "--evidence", "https://example.com/m", "--expires", "2029-01-01"); run("sync")
        self.use(self.B); run("sync")
        self.use(self.A); run("sweep"); self.assertEqual(run("sync")[0], 0)
        self.use(self.B); run("sweep"); c, o = run("sync"); self.assertEqual(c, 0, o)
        self.assertEqual(fold_status(i), "expired")

    def test_push_retry_when_remote_moves(self):
        self.use(self.A); self.add("work", "a1"); run("sync")
        self.use(self.B); run("sync"); self.add("work", "b1")
        # remote moves between B's commit and push: A pushes in the middle
        self.use(self.A); self.add("work", "a2"); run("sync")
        self.use(self.B); self.assertEqual(run("sync")[0], 0)
        self.assertEqual(len(pandu.fold()), 3)

    def test_same_name_different_content_aborts_merge(self):
        self.use(self.A); self.add("work", "x"); run("sync")
        self.use(self.B); run("sync")
        fn = os.listdir(os.path.join(self.A, "events"))[0]
        self.use(self.A)
        p = os.path.join(self.A, "events", fn)
        self.tamper(p, "tampered A")
        run("sync")
        self.use(self.B)
        p = os.path.join(self.B, "events", fn)
        self.tamper(p, "tampered B")
        c, o = run("sync")
        self.assertNotEqual(c, 0)
        self.assertEqual(self.g(self.B, "status", "--porcelain").count("UU"), 0)

    def test_public_sync_refuses_unsafe_event_files_before_commit(self):
        self.use(self.A)
        run("init", "--visibility", "public", "--deny", "secret-repo")
        self.assertEqual(run("add", "work", "ok", "--public-ok")[0], 0)
        self.assertEqual(run("sync")[0], 0)
        pandu.write_event({"op": "add", "entry": "leak00000001", "parents": [], "at": "x",
                           "fields": {"kind": "work", "title": "from secret-repo"}}, "leak00000001")
        before = self.g(self.A, "rev-parse", "HEAD")
        c, o = run("sync")
        self.assertNotEqual(c, 0); self.assertIn("not allowed in a public log", o)
        self.assertEqual(self.g(self.A, "rev-parse", "HEAD"), before)
        self.assertNotIn("leak00000001", self.g(self.A, "ls-files"))
        self.assertEqual(self.g(self.bare, "log", "--all", "--oneline").count("\n"), 1)

    def remote_log(self):
        r = subprocess.run(["git", "--git-dir", self.bare, "log", "--all", "--oneline"], capture_output=True, text=True)
        return r.stdout

    def test_deny_strings_never_reach_tracked_files_or_history(self):
        self.use(self.A)
        run("init", "--visibility", "public", "--deny", "secret-repo")
        run("add", "work", "ok", "--public-ok"); self.assertEqual(run("sync")[0], 0)
        tracked = self.g(self.A, "ls-files")
        self.assertNotIn("pandu.local.json", tracked)
        with open(os.path.join(self.A, ".gitignore")) as f:
            self.assertIn("pandu.local.json", f.read())
        allhist = self.g(self.A, "log", "--all", "-p")
        self.assertNotIn("secret-repo", allhist)
        self.assertEqual(os.stat(os.path.join(self.A, "pandu.local.json")).st_mode & 0o777, 0o600)
        with open(os.path.join(self.A, "pandu.json")) as f:
            self.assertNotIn("deny", f.read())

    def test_history_with_a_deny_in_config_blob_is_refused(self):
        self.use(self.A)
        run("add", "work", "ok", "--public-ok")
        with open(os.path.join(self.A, "pandu.json"), "w") as f:
            json.dump({"visibility": "public", "deny": ["secret-repo"]}, f)
        c, o = run("sync"); self.assertNotEqual(c, 0)
        self.assertEqual(self.remote_log(), "")

    def test_denied_string_in_readme_or_commit_metadata_blocks_push(self):
        self.use(self.A)
        run("init", "--visibility", "public", "--deny", "secret-repo")
        run("add", "work", "ok", "--public-ok")
        with open(os.path.join(self.A, "README.md"), "w") as f:
            f.write("data for Secret-Repo")
        self.g(self.A, "add", "README.md"); self.g(self.A, "commit", "-q", "-m", "readme")
        c, o = run("sync"); self.assertNotEqual(c, 0); self.assertIn("denied string in 'README.md'", o)
        self.assertEqual(self.remote_log(), "")
        self.g(self.A, "rm", "-q", "-f", "README.md")
        self.g(self.A, "commit", "-q", "-m", "drop it")
        self.assertNotEqual(run("sync")[0], 0)  # still in history, so still blocked

    def test_denied_string_in_author_or_message_blocks_push(self):
        self.use(self.A)
        run("init", "--visibility", "public", "--deny", "secret-repo")
        run("add", "work", "ok", "--public-ok")
        c, o = run("sync", "--message", "about secret-repo")
        self.assertNotEqual(c, 0); self.assertIn("commit metadata", o)
        self.assertEqual(self.remote_log(), "")

    def test_unrelated_staged_paths_are_never_committed(self):
        self.use(self.A)
        run("add", "work", "ok", "--public-ok")
        with open(os.path.join(self.A, "notes.txt"), "w") as f:
            f.write("private")
        self.g(self.A, "add", "notes.txt")
        c, o = run("sync"); self.assertNotEqual(c, 0); self.assertIn("unrelated paths are staged", o)
        self.assertEqual(self.remote_log(), "")

    def test_unrelated_tracked_file_or_history_blocks_push(self):
        self.use(self.A)
        run("add", "work", "ok", "--public-ok")
        with open(os.path.join(self.A, "notes.txt"), "w") as f:
            f.write("private")
        self.g(self.A, "add", "notes.txt"); self.g(self.A, "commit", "-q", "-m", "unrelated")
        self.g(self.A, "rm", "-q", "-f", "notes.txt"); self.g(self.A, "commit", "-q", "-m", "removed again")
        c, o = run("sync")  # the file is gone from the tree but still in history
        self.assertNotEqual(c, 0); self.assertIn("unrelated path 'notes.txt'", o)
        self.assertEqual(self.remote_log(), "")

    def test_foreign_remote_history_is_not_merged_or_pushed(self):
        other = os.path.join(self.t, "O")
        self.g(self.t, "init", "-q", "-b", "main", other)
        with open(os.path.join(other, "app.py"), "w") as f:
            f.write("x")
        self.g(other, "add", "."); self.g(other, "commit", "-q", "-m", "app")
        self.g(other, "push", "-q", self.bare, "HEAD:main")
        self.use(self.A)
        run("add", "work", "mine", "--public-ok")
        c, o = run("sync"); self.assertNotEqual(c, 0); self.assertIn("unrelated path 'app.py'", o)
        self.assertEqual(self.remote_log().count("\n"), 1)

    def test_invalid_graph_is_never_committed_or_pushed(self):
        self.use(self.A)
        i = self.add("agreed", "G", "--evidence", "https://example.com/m")
        pandu.write_event({"op": "correct", "entry": i, "parents": ["deadbeefdead"], "fields": {"notes": "x"},
                           "previous": {}, "reason": "", "at": "x"})
        before = subprocess.run(["git", "-C", self.A, "rev-parse", "--verify", "-q", "HEAD"], capture_output=True).returncode
        c, o = run("sync"); self.assertNotEqual(c, 0); self.assertIn("missing parent", o)
        self.assertNotEqual(before, 0)  # still no commit at all
        self.assertEqual(subprocess.run(["git", "-C", self.A, "rev-parse", "--verify", "-q", "HEAD"], capture_output=True).returncode, before)
        self.assertEqual(self.remote_log(), "")

    def test_invalid_graph_arriving_from_remote_is_not_pushed_onward(self):
        self.use(self.A)
        i = self.add("agreed", "G", "--evidence", "https://example.com/m"); run("sync")
        # a second clone pushes a dangling-parent event straight to the remote
        other = os.path.join(self.t, "B2")
        self.g(self.t, "clone", "-q", self.bare, other)
        os.environ["PANDU_DIR"] = other
        pandu.write_event({"op": "correct", "entry": i, "parents": ["deadbeefdead"], "fields": {"notes": "x"},
                           "previous": {}, "reason": "", "at": "x"})
        self.g(other, "add", "events"); self.g(other, "commit", "-q", "-m", "bad"); self.g(other, "push", "-q", "origin", "HEAD:main")
        tip = self.g(self.t, "--git-dir", self.bare, "rev-parse", "main") if False else subprocess.run(
            ["git", "--git-dir", self.bare, "rev-parse", "main"], capture_output=True, text=True).stdout
        self.use(self.A)
        self.add("work", "mine")
        c, o = run("sync"); self.assertNotEqual(c, 0); self.assertIn("missing parent", o)
        after = subprocess.run(["git", "--git-dir", self.bare, "rev-parse", "main"], capture_output=True, text=True).stdout
        self.assertEqual(tip, after)  # our commit was not pushed on top of the invalid graph

    REF = "89f1884da65eba62838862f966ec7a0003e5bbe4"

    def test_scaffold_files_and_workflow_invariants(self):
        out = os.path.join(self.t, "scaf")
        self.assertEqual(run("scaffold", out, "--pandu-ref", self.REF)[0], 0)
        wf = open(os.path.join(out, ".github", "workflows", "sweep.yml")).read() if False else None
        with open(os.path.join(out, ".github", "workflows", "sweep.yml")) as f:
            wf = f.read()
        self.assertIn(self.REF, wf); self.assertNotIn("__PANDU_REF__", wf)
        self.assertIn("permissions:\n  contents: write", wf)
        self.assertIn("concurrency:", wf); self.assertIn("cancel-in-progress: false", wf)
        self.assertIn("fetch-depth: 0", wf); self.assertIn("timeout-minutes", wf)
        self.assertNotIn("secrets.", wf)
        self.assertIn("persist-credentials: false", wf)
        self.assertEqual(wf.count("github.token"), 1)  # the automatic token reaches one step only
        self.assertLess(wf.index("persist-credentials"), wf.index("github.token"))
        self.assertEqual(len(re.findall(r"uses: \S+@[0-9a-f]{40}", wf)), wf.count("uses:"))
        self.assertNotIn("pull_request", wf)
        with open(os.path.join(out, "pandu.json")) as f:
            self.assertEqual(json.load(f), {"visibility": "public"})
        self.assertFalse(os.path.exists(os.path.join(out, "events")))
        self.assertNotEqual(run("scaffold", out, "--pandu-ref", self.REF)[0], 0)  # never overwrites
        self.assertNotEqual(run("scaffold", os.path.join(self.t, "x"), "--pandu-ref", "main")[0], 0)

    def test_scaffold_needs_an_empty_directory(self):
        d = os.path.join(self.t, "ne"); os.makedirs(d)
        open(os.path.join(d, "notes.txt"), "w").close()
        c, o = run("scaffold", d, "--pandu-ref", self.REF); self.assertNotEqual(c, 0)
        self.assertEqual(os.listdir(d), ["notes.txt"])  # nothing written
        e = os.path.join(self.t, "ne2"); os.makedirs(e)
        os.symlink(d, os.path.join(e, "sub"))
        self.assertNotEqual(run("scaffold", e, "--pandu-ref", self.REF)[0], 0)
        link = os.path.join(self.t, "lnk"); os.symlink(d, link)
        self.assertNotEqual(run("scaffold", link, "--pandu-ref", self.REF)[0], 0)
        gd = os.path.join(self.t, "ne3"); os.makedirs(gd)
        self.g(gd, "init", "-q")  # only .git is allowed
        self.assertEqual(run("scaffold", gd, "--pandu-ref", self.REF)[0], 0)

    @staticmethod
    def rd(p):
        with open(p) as f:
            return f.read()

    @staticmethod
    def wr(p, t):
        with open(p, "w") as f:
            f.write(t)

    def scaffolded(self):
        out = self.A
        self.assertEqual(run("scaffold", out, "--pandu-ref", self.REF)[0], 0)
        for k, v in (("user.name", "t"), ("user.email", "t@example.invalid")):
            self.g(out, "config", k, v)
        self.g(out, "add", "."); self.g(out, "commit", "-q", "-m", "scaffold"); self.g(out, "push", "-q", "origin", "HEAD:main")
        os.environ["PANDU_DIR"] = out
        return out

    def test_workflow_must_stay_the_reviewed_template(self):
        out = self.scaffolded()
        wf = os.path.join(out, ".github", "workflows", "sweep.yml")
        good = self.rd(wf)
        # a new reviewed hash is fine
        new = good.replace(self.REF, "a" * 40)
        self.wr(wf, new); self.g(out, "commit", "-qam", "bump")
        self.assertEqual(run("sync")[0], 0)
        # uncommitted tamper in the working file
        self.wr(wf, new + "      - run: echo extra\n")
        c, o = run("sync"); self.assertNotEqual(c, 0); self.assertIn("reviewed template", o)
        # committed tamper, then restored: history still carries it, so nothing is pushed
        self.g(out, "commit", "-qam", "tamper"); self.wr(wf, new); self.g(out, "commit", "-qam", "restore")
        c, o = run("sync"); self.assertNotEqual(c, 0); self.assertIn("reviewed template", o)
        self.assertNotIn("echo extra", subprocess.run(["git", "--git-dir", self.bare, "log", "-p", "main"], capture_output=True, text=True).stdout)

    def test_workflow_removal_and_unpinned_ref_fail_closed(self):
        out = self.scaffolded()
        wf = os.path.join(out, ".github", "workflows", "sweep.yml")
        good = self.rd(wf)
        self.wr(wf, good.replace(self.REF, "main"))
        c, o = run("sync"); self.assertNotEqual(c, 0); self.assertIn("pinned", o)
        self.wr(wf, good)
        os.remove(wf)
        c, o = run("sync"); self.assertNotEqual(c, 0); self.assertIn("removed", o)
        self.g(out, "rm", "-q", "--cached", ".github/workflows/sweep.yml"); self.g(out, "commit", "-qm", "rm")
        c, o = run("sync"); self.assertNotEqual(c, 0); self.assertIn("removes the workflow", o)

    def ci(self, where):
        """The same commands the workflow runs."""
        os.environ["PANDU_DIR"] = where
        return [run("sweep"), run("sync", "--message", "Record expired grants"), run("check")]

    def test_scheduled_routine_end_to_end(self):
        out = self.A
        self.assertEqual(run("scaffold", out, "--pandu-ref", self.REF)[0], 0)
        for k, v in (("user.name", "t"), ("user.email", "t@example.invalid")):
            self.g(out, "config", k, v)
        self.g(out, "add", "."); self.g(out, "commit", "-q", "-m", "scaffold")
        self.g(out, "push", "-q", "origin", "HEAD:main")
        os.environ["PANDU_DIR"] = out
        i = self.add("agreed", "Public grant", "--evidence", "https://example.com/d", "--expires", "2000-01-01")
        self.assertEqual(run("sync")[0], 0)
        # fresh full clone, like the Action's checkout, runs the routine
        ci = os.path.join(self.t, "ci")
        self.g(self.t, "clone", "-q", self.bare, ci)
        for k, v in (("user.name", "github-actions[bot]"), ("user.email", "bot@example.invalid")):
            self.g(ci, "config", k, v)
        res = self.ci(ci)
        self.assertEqual([c for c, _ in res], [0, 0, 0], res)
        os.environ["PANDU_DIR"] = out
        self.assertEqual(run("sync")[0], 0)
        self.assertEqual(fold_status(i), "expired")
        self.assertEqual(run("check")[0], 0)
        # running the routine again the same day changes nothing
        n = self.remote_log().count("\n")
        self.assertEqual([c for c, _ in self.ci(ci)], [0, 0, 0])
        self.assertEqual(self.remote_log().count("\n"), n)

    def test_scheduled_routine_surfaces_a_conflict_as_a_failed_run(self):
        out = self.A
        run("scaffold", out, "--pandu-ref", self.REF)
        for k, v in (("user.name", "t"), ("user.email", "t@example.invalid")):
            self.g(out, "config", k, v)
        self.g(out, "add", "."); self.g(out, "commit", "-q", "-m", "scaffold"); self.g(out, "push", "-q", "origin", "HEAD:main")
        os.environ["PANDU_DIR"] = out
        i = self.add("agreed", "G", "--evidence", "https://example.com/d", "--expires", "2099-01-01"); run("sync")
        ci = os.path.join(self.t, "ci")
        self.g(self.t, "clone", "-q", self.bare, ci)
        os.environ["PANDU_DIR"] = out
        run("correct", i, "--expires", "2099-02-01", "--public-ok"); run("sync")
        os.environ["PANDU_DIR"] = ci
        run("resolve", i, "revoked", "--public-ok"); run("sync")
        res = self.ci(ci)
        self.assertEqual(res[2][0], 1)  # check fails, so the run is red and GitHub notifies

    def test_private_log_cannot_sync(self):
        os.environ["PANDU_DIR"] = self.A
        run("init", "--visibility", "private")
        run("add", "work", "private thing")
        c, o = run("sync"); self.assertNotEqual(c, 0); self.assertIn("PUBLIC log", o)
        os.environ["PANDU_DIR"] = self.B  # no config at all is private too
        run("add", "work", "private two")
        self.assertNotEqual(run("sync")[0], 0)
        self.assertEqual(self.remote_log(), "")

    def test_not_a_repo(self):
        os.environ["PANDU_DIR"] = self.d.name
        run("init", "--visibility", "public")
        c, o = run("sync")
        self.assertNotEqual(c, 0)


if __name__ == "__main__":
    unittest.main()
