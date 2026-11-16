#!/usr/bin/env python3
"""Scripted local rehearsal of the delivery and checkpoint commands, with made-up data.

What this is: a small simulated caller (`deliver`) that runs the runbook steps in order against the
real pandu commands, in temporary folders, with a fake chat file and a fake store (numbered copies).
What this is not: proof of any real send, real storage, real encryption, two machines at once, or a
real chat. It sends nothing and touches no account.
Run: python3 tests/rehearsal.py"""
import json, os, shutil, subprocess, sys, tempfile

PANDU = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools", "pandu.py")
ENV = dict(os.environ, PANDU_TEST_MODE="1", PANDU_TODAY="2026-06-10")
results = []


def check(name, cond):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


class Case:
    """One case: its own log, sent file, chat file and store, and one made-up grant (so its own key)."""

    def __init__(self, root, name):
        self.dir = os.path.join(root, name)
        os.makedirs(os.path.join(self.dir, "store"))
        self.log, self.sent, self.chat = (os.path.join(self.dir, n) for n in ("log", "sent.txt", "chat.txt"))
        self.store = os.path.join(self.dir, "store")
        self.gen = 0
        self.pandu("add", "agreed", f"Example grant {name}", "--evidence", "example reference", "--expires", "2026-06-10")
        n = self.due()["notices"]
        self.key, self.msg = n[0]["key"], n[0]["message"]

    def pandu(self, *args, log=None, ok=True):
        r = subprocess.run([sys.executable, PANDU, *args], capture_output=True, text=True,
                           env=dict(ENV, PANDU_DIR=log or self.log))
        if ok and r.returncode != 0:
            raise SystemExit(f"FAILED: pandu {' '.join(args)}\n{r.stdout}{r.stderr}")
        return r

    def due(self, sent=None, log=None):
        return json.loads(self.pandu("due", "--format", "json", "--sent-file", sent or self.sent, log=log).stdout)

    def chat_count(self):  # how many messages carry this key
        return sum(self.key in l for l in open(self.chat).read().splitlines()) if os.path.exists(self.chat) else 0

    def put_chat(self, text):
        with open(self.chat, "a") as f:
            f.write(text + "\n")

    def store_checkpoint(self, publish=True):
        self.n = getattr(self, "n", 0) + 1
        tmp = os.path.join(self.dir, f"cp{self.n}.json")  # a new file each time, so an older copy stays as it was
        self.pandu("checkpoint", "export", tmp, "--sent-file", self.sent)
        if publish:
            self.gen += 1
            shutil.copy(tmp, os.path.join(self.store, f"gen{self.gen}.json"))
        return tmp

    def latest(self):
        return os.path.join(self.store, f"gen{self.gen}.json")

    def covers(self):
        """The real covers command, run on the stored copy. Returns its exit code."""
        if self.gen == 0:
            return 1
        return self.pandu("checkpoint", "covers", self.latest(), "--sent-file", self.sent, "--key", self.key, ok=False).returncode

    def deliver(self, covers=None, publish=True, crash_after_send=False, verify_delivered=True, skip_seen=False):
        """The runbook steps for one notice. Returns what happened.
        covers: override for the covers step, used only to show a broken caller. verify_delivered: whether
        the caller has real evidence the notice was delivered (a draft or quoted text is not evidence)."""
        d = self.due()
        if d["uncertain"]:
            return "stopped: uncertain keys"
        if self.key not in [x["key"] for x in d["notices"]]:
            return "nothing to send"
        if os.path.exists(self.chat) and not skip_seen:  # step 2, automatic: the ref is already in the chat export. Hold it, never mark sent.
            seen = json.loads(self.pandu("due", "--format", "json", "--sent-file", self.sent, "--seen-in", self.chat).stdout)
            if self.key in [x["key"] for x in seen["uncertain"]]:
                return "stopped: ref found in chat, manual check"
        self.pandu("due", "--sent-file", self.sent, "--mark-attempt", self.key)
        self.store_checkpoint(publish=publish)
        if (covers or self.covers)() != 0:
            return "stopped: covers failed"
        self.put_chat(self.msg)  # the simulated send
        if crash_after_send:
            raise RuntimeError("simulated crash after the send")
        if not verify_delivered:
            return "sent, outcome unknown, left uncertain"
        self.pandu("due", "--sent-file", self.sent, "--mark-sent", self.key)
        self.store_checkpoint()  # post-send export
        return "delivered"

    def restore(self, checkpoint, name):
        new_log, new_sent = os.path.join(self.dir, name + "-log"), os.path.join(self.dir, name + "-sent.txt")
        self.pandu("checkpoint", "restore", checkpoint, "--into", new_log, "--sent-file", new_sent)
        return new_log, new_sent


def main(root):
    # A: normal delivery, and the post-send copy really holds the delivery
    a = Case(root, "A")
    check("A delivered", a.deliver() == "delivered" and a.chat_count() == 1)
    log, sent = a.restore(a.latest(), "r")
    d = a.due(sent, log)
    check("A the latest stored copy restores to nothing pending or uncertain", d["notices"] == [] and d["uncertain"] == [])
    check("A a second run does nothing", a.deliver() == "nothing to send" and a.chat_count() == 1)

    # B1: nothing was stored at all, B2: a copy is stored but it holds no attempt for this key
    b1 = Case(root, "B1")
    check("B1 no stored copy: no send", b1.deliver(publish=False) == "stopped: covers failed" and b1.chat_count() == 0)
    b2 = Case(root, "B2")
    b2.store_checkpoint()  # an old copy exists, taken before any attempt
    r = b2.deliver(publish=False)  # the attempt is recorded but the newest state was not stored
    check("B2 old stored copy (stale, no attempt): no send", r == "stopped: covers failed" and b2.chat_count() == 0)
    # the same two cases through a caller that ignores the covers exit would send. This shows the checks are not vacuous.
    m1 = Case(root, "M1")
    check("M1 a mutant caller that ignores covers does send (B1 case)", m1.deliver(publish=False, covers=lambda: 0) == "delivered" and m1.chat_count() == 1)
    m2 = Case(root, "M2")
    m2.store_checkpoint()
    check("M2 a mutant caller that ignores covers does send (B2 case)", m2.deliver(publish=False, covers=lambda: 0) == "delivered" and m2.chat_count() == 1)

    # C: crash after the send, before mark-sent, then a reset and a restore
    c = Case(root, "C")
    try:
        c.deliver(crash_after_send=True)
    except RuntimeError:
        pass
    log, sent = c.restore(c.latest(), "r")
    d = c.due(sent, log)
    check("C after the reset the key is uncertain, not pending", d["notices"] == [] and [x["key"] for x in d["uncertain"]] == [c.key])
    c.log, c.sent = log, sent  # the caller now runs on the restored state
    r = c.deliver()
    check("C a caller run on the restored state stops as uncertain and sends nothing",
          r == "stopped: uncertain keys" and c.chat_count() == 1)
    # the person verifies real delivery, which this rehearsal represents by an explicit decision
    c.pandu("due", "--sent-file", sent, "--mark-sent", c.key)
    d = c.due()
    check("C settled by a verified delivery: nothing pending", d["notices"] == [] and d["uncertain"] == [])

    # D1: restore from a copy older than the attempt, with the ref still in the chat
    d1 = Case(root, "D1")
    old = d1.store_checkpoint(publish=False)
    d1.deliver()
    log, sent = d1.restore(old, "old")
    d1.log, d1.sent = log, sent
    check("D1 older copy and ref in chat: the caller stops, no second message",
          d1.deliver() == "stopped: ref found in chat, manual check" and d1.chat_count() == 1)
    held = json.loads(d1.pandu("due", "--format", "json", "--sent-file", d1.sent, "--seen-in", d1.chat).stdout)
    recorded = open(d1.sent).read().splitlines() if os.path.exists(d1.sent) else []
    check("D1 the key is held as uncertain by --seen-in, and no delivery was recorded",
          [x["key"] for x in held["uncertain"]] == [d1.key] and not held["notices"] and d1.key not in recorded)
    # the same case through a caller that skips the --seen-in step does send again: the check is not empty
    d1m = Case(root, "D1M")
    old = d1m.store_checkpoint(publish=False)
    d1m.deliver()
    log, sent = d1m.restore(old, "old")
    d1m.log, d1m.sent = log, sent
    check("M3 a mutant caller that skips --seen-in sends again", d1m.deliver(skip_seen=True) == "delivered" and d1m.chat_count() == 2)
    # D2: the same, but the chat history is lost
    d2 = Case(root, "D2")
    old = d2.store_checkpoint(publish=False)
    d2.deliver()
    os.remove(d2.chat)  # history lost
    log, sent = d2.restore(old, "old")
    d2.log, d2.sent = log, sent
    check("D2 KNOWN GAP: older copy and lost chat: the notice is sent again", d2.deliver() == "delivered" and d2.chat_count() == 1)

    # D3: older copy, chat lost, but the caller kept a small witness (the sent-record line count at the last
    # publish) somewhere other than the stored copy. The restore refuses the older copy.
    d3 = Case(root, "D3")
    old = d3.store_checkpoint(publish=False)
    d3.deliver()
    witness = open(d3.sent).read().count("\n")  # the caller records this number after each publish
    os.remove(d3.chat)
    r = d3.pandu("checkpoint", "restore", old, "--into", os.path.join(d3.dir, "old3"), "--sent-file", os.path.join(d3.dir, "old3-sent.txt"),
                 "--min-records", str(witness), ok=False)
    check("D3 older copy, chat lost, witness kept: the restore is refused", r.returncode != 0 and not os.path.exists(os.path.join(d3.dir, "old3")))
    log, sent = d3.restore(d3.latest(), "new")
    d3.log, d3.sent = log, sent
    check("D3 the newest copy restores and nothing is pending", d3.due()["notices"] == [] and d3.due()["uncertain"] == [])

    # E: the chat text matches but was a draft, never delivered. The caller must not mark it sent.
    e = Case(root, "E")
    e.put_chat("draft, not delivered: " + e.msg)
    check("E text found in chat: stopped and nothing recorded as sent",
          e.deliver() == "stopped: ref found in chat, manual check"
          and not os.path.exists(e.sent))
    # the cost is stated in the runbook: a match that is not a delivery can drop a notice until a person decides

    # F: sent but delivery not verified
    f = Case(root, "F")
    check("F sent with unknown outcome stays uncertain", f.deliver(verify_delivered=False) == "sent, outcome unknown, left uncertain"
          and f.due()["uncertain"] and not f.due()["notices"])

    # G: refusals
    g = Case(root, "G"); g.deliver()
    cp = g.latest()
    check("G restore refuses to drop the sent record", g.pandu("checkpoint", "restore", cp, "--into", os.path.join(g.dir, "x1"), ok=False).returncode != 0)
    check("G restore refuses a non-empty folder", g.pandu("checkpoint", "restore", cp, "--into", g.log, "--sent-file", os.path.join(g.dir, "s9.txt"), ok=False).returncode != 0)
    t = json.load(open(cp)); t["sent"] = ""
    bad = os.path.join(g.dir, "tampered.json"); json.dump(t, open(bad, "w"))
    check("G an edited checkpoint is refused", g.pandu("checkpoint", "verify", bad, ok=False).returncode != 0)


if __name__ == "__main__":
    root = tempfile.mkdtemp(prefix="pandu-rehearsal-")
    try:
        main(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    bad = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(bad)} of {len(results)} checks passed")
    sys.exit(1 if bad else 0)
