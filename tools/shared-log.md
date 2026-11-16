# Keeping a public log in a GitHub data repository

The tool in this folder is local. To share a **public** log of curated entries, put it in a dedicated data repository, not in this code repository. Real private entries never belong in either one.

## Layout

- Code: this repository (public, generic).
- Public data repository: dedicated to pandu data. It holds only the `events/` folder, `pandu.json` (the visibility setting only), and optionally `.gitignore` and `README.md`. Set `PANDU_DIR=.` inside a checkout of it.
- `pandu sync` refuses any repository whose history contains anything else, and it only ever works for a log set to public. A private log is never pushed anywhere by this tool.

## Public log on GitHub, private entries elsewhere

Real entries that are sensitive do not go in GitHub. Two arrangements fit:

- **Public log**: a separate data repository for entries written for public readers. Run `pandu init --visibility public --deny PRIVATE-NAME` once. From then on every write needs `--public-ok` (your confirmation that the words are fit for public readers), evidence must be a public http(s) link, and any denied string is refused. The deny strings live only in `pandu.local.json` on your machine (git-ignored, mode 0600) and are never written to the repository or its history. `sync` only ever commits `events/` and `pandu.json`, refuses if anything else is staged, and checks the full event graph (missing parents, cycles, damaged files), the public rules and the complete reachable history (every event, config and other text file, plus commit author, committer and message text, checked for your denied strings) before the local commit and again after the merge, before every push. Unrelated files anywhere in the history, edited or removed event files, or foreign history on the remote stop the sync with nothing pushed.
- **Private log**: the default (`init --visibility private`, or no config), kept only on storage you control. `sync` refuses to run on it, so private entries, evidence and approval links are never pushed by this tool, and they must not go in a public repository's workflows or artifacts either. Nothing is copied from one log to the other and there is no backfill of old conversations. If unsure which log an entry belongs in, use the private one.

`pandu outbox` formats unreported changes (new entries, corrections, resolutions, expiries) as plain-text messages for a private channel such as a chat app, and lists open conflicts and expired-but-open grants. It only formats text and sends nothing. After you have really delivered them, `pandu outbox --mark-sent` records that locally so they are not repeated. A chat message is a notification, not the record: the log stays the source of truth and the message is never executable state.

Each message carries a stable entry reference, a version (the event id) and the version it replaces, so a reader can tell a correction from a new entry. A delivered message is not an approval, and a chat app is not storage: keep the private log itself on durable storage you control and back it up, because messages can be lost and are not an executable record. Expiry dates are plain calendar dates compared with the local date of the machine running `sweep`.

## Limits, stated plainly

- The public checks (`--public-ok`, the http(s) evidence rule and the deny strings) are friction for the person writing, not proof of confidentiality. The tool cannot classify text. A public log is for entries you have deliberately curated for public readers. A link that looks like a public URL can still point somewhere private, and a deny list only catches what you thought to list.
- Low-entropy names are not hidden by hashing, so deny strings are simply kept local.
- Git history is permanent and public once pushed. Nothing here can take a published entry back.
- There is no cryptographic authentication of events. A git author name and email can be set to anything, so they are not proof of who wrote an entry. What actually controls who can write is the host's access control and push credentials, which the tool does not manage. A well-formed but wrong event from someone with push access is accepted.
- There is no direct chat adapter, no scheduler and no revocation of any real access. `outbox` only formats text, and delivery, scheduling and durable storage of a private log are up to you.

Automation is limited to what needs no judgment: `sweep`, `sync` for a public log, and `outbox`. A scheduled job can record expiries and push them, but it cannot create or approve entries, and recording an expiry grants nothing. Do not run any job that touches private entries in a public repository's workflows.

## How concurrent writers are handled

- Each event is its own file named by a unique id, so adding events on two machines never produces a git conflict. `pandu sync` commits new events, fetches the remote, merges, pushes, and retries if the remote moved. It always runs a full integrity check on the merged history.
- The only possible git conflict is two different files with the same name. The merge is aborted and nothing is overwritten.
- Git merging is not the same as agreeing. If two people changed the same entry from the same starting point, `pandu` marks the entry as a conflict and fails closed (see the README). Neither change wins by clock order or merge order, and a grant is never silently extended or revived. Someone runs `settle` to decide.
- Git history shows who committed what and when, on top of the log's own history.
- Tests cover two local clones plus a bare remote: simultaneous adds, a push retried after the remote moved, a concurrent extend-versus-revoke becoming a conflict, two machines sweeping the same day, and a same-name collision aborting the merge. They use no network.

## Deterministic expiry

`pandu sweep` is a plain program with no judgement in it: any open grant whose expiry date is before today is recorded as `expired`. The event id is derived from the entry, its history and the date, so two machines sweeping the same day write the identical file and cannot conflict. `pandu check` exits 1 while an expired grant is open or an entry is in conflict. (`PANDU_TODAY` exists only for tests and is refused without `PANDU_TEST_MODE=1`.)

Recording an expiry does not remove access. That is a separate step done where the access was granted (repository settings, a shared folder, a token). The status page lists such grants under "Expired: access removal not confirmed" until someone removes the access and runs `pandu resolve ID revoked --note "..."`. Automating the removal itself would need an adapter per service, with credentials that are allowed to remove that exact access. This tool has none.

## A scheduled job in the data repo (example, not enabled anywhere)

    name: sweep
    on:
      schedule: [{cron: "17 2 * * *"}]
      workflow_dispatch:
    permissions: {contents: write}
    jobs:
      sweep:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - run: git clone --depth 1 https://github.com/OWNER/pandu /tmp/pandu
          - run: |
              git config user.name "pandu sweep"
              git config user.email "sweep@users.noreply.github.com"
              export PANDU_DIR=.
              python3 /tmp/pandu/tools/pandu.py sweep
              python3 /tmp/pandu/tools/pandu.py sync --message "Record expired grants"

Pin the clone to a commit you have reviewed. The job only adds files under `events/` in the data repo.
