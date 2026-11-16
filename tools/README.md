# pandu tool

A small command line tool for the three proposals in [tools.md](../tools.md): a decision and permission log, a status page, and grant templates. Python 3.10+, standard library only, no network, no accounts.

## What this first version is

A local, single-machine command line tool plus a static status export. It is not a live shared page: there is no sync, so to share the status you send or host the exported file yourself. It does not enforce permissions, it does not actually revoke access when a grant expires (`sweep` only records the expiry), and it sends no notifications. Someone still has to do those things.

## Privacy

Data stays on your machine, in `.pandu/events/` (or the directory in `PANDU_DIR`), one small file per event. The tool never sends anything anywhere.

- The data directory is created with mode 0700, and event files and any status export are written with mode 0600. These are ordinary file permissions and only protect against other users on the same machine.
- `.gitignore` keeps `.pandu/` and `status.*` exports out of commits by default, but a gitignore is not access control. Do not put the log in a public repo or a shared folder you do not trust. Entries may contain names, scopes and links.
- The status export is a plain snapshot. Whoever can read the file can read everything in it.

See [shared-log.md](shared-log.md) for a public log in a GitHub data repository, its limits, and scheduled expiry.

## How history stays trustworthy

- **One immutable file per event.** Events are never edited or deleted. Two machines adding events never touch the same file, so git merges them without conflicts.
- **Order comes from parent links, not clocks.** Each correction or resolution names the event it was based on. If two changes start from the same point (for example one person extends a grant while another revokes it), the entry is shown as a **conflict**: not active, not valid, and nothing can be corrected or resolved until someone runs `settle`, which merges both heads explicitly. A timestamp, even one far in the future, cannot revive or extend a grant.
- **Closed means closed.** An edit never reopens a revoked, expired or denied entry. Add a new entry instead.
- **Damaged or incomplete history stops everything.** A bad event file, a missing parent or a missing first event makes every command exit with an error naming the file, and nothing is written.
- **`PANDU_TODAY` is test-only.** It is refused unless `PANDU_TEST_MODE=1` is also set, so it can never quietly change which grants count as valid.

## Use

    alias pandu="python3 tools/pandu.py"
    pandu grant push-access --set repo=demo --set project=docs --expires 2026-12-31 --evidence "message of 1 Dec"
    pandu add approval "Publish the draft page"
    pandu add waiting "DNS change" --waiting-on owner
    pandu add work "Write the report" --next-actor assistant
    pandu correct ID --expires 2027-01-31 --reason "owner extended it"
    pandu resolve ID approved --note "owner said yes"
    pandu sweep          # record expired grants (deterministic, same result on any machine)
    pandu settle ID revoked --note "why"   # explicitly merge a conflict
    pandu due [--within DAYS] [--format json]   # expiry notices due, with stable keys; read-only
    pandu due --sent-file F [--mark-attempt|--mark-sent|--clear-attempt KEY...]   # delivery record with an uncertain state
    pandu checkpoint export|verify|restore FILE   # log + sent record in one plain file, see checkpoint.md
    # runbook.md: the manual routine; tests/rehearsal.py runs it with made-up data
    pandu scaffold DIR --pandu-ref HASH   # files for a public data repo, with the daily expiry job
    pandu init --visibility public --deny PRIVATE-REPO-NAME   # a public log: writes then need --public-ok
    pandu outbox         # plain-text messages for changes not yet reported (sends nothing)
    pandu outbox --mark-sent   # after you delivered them
    pandu sync           # public log only: verify, commit events, merge the remote, verify again, push
    pandu check          # exit 1 if an expired grant is still open
    pandu list --all
    pandu show ID
    pandu status --format html --out status.html
    pandu status --view brief    # only what needs action; default is the full view
    pandu templates

Kinds: `agreed`, `waiting`, `approval`, `work`. Resolutions: approved, denied, done, expired, revoked, archived. Templates are JSON files in `templates/`; add your own.

Run the tests: `python3 -m unittest discover -s tests`
