# Checkpoint file

`kaidah checkpoint` packs a private log and its sent record into one plain JSON file, so the pair can be stored somewhere durable and restored after a reset. It is plain text. Encrypt it before it is stored, and keep the key elsewhere. Kaidah stores nothing and sends nothing.

## Commands

    kaidah checkpoint export FILE [--sent-file PATH]     # writes FILE (mode 0600), never overwrites
    kaidah checkpoint verify FILE                         # reads only; exit 0 means valid
    kaidah checkpoint restore FILE --into DIR [--sent-file PATH] [--min-records N]   # DIR must be empty or new; PATH must not exist
    kaidah checkpoint covers FILE --sent-file PATH [--key KEY]      # exit 0 only if FILE equals the current state

`verify` and `restore` check everything before they write anything. Any doubt stops them with nothing changed: a different `format`, a missing or extra field, a checksum mismatch, an event whose name does not match its `eid`, an event with a missing parent or a cycle, or a bad sent record. `--min-records N` refuses a checkpoint whose sent record has fewer than N lines. Within one history the record only grows, so a smaller count means an older copy of that history. The check compares line counts only. A copy from a different history with the same or a larger count passes, and so does any copy when the number you pass is out of date. `verify` prints the count, and the caller keeps the last one outside the stored copy (see `runbook.md`). `restore` refuses a checkpoint that carries a sent record unless `--sent-file` is given, so a record is never dropped silently. It builds everything aside in a temporary folder next to the target, then publishes the sent record (never over an existing file) and renames the folder into place. If an error it can catch happens, it removes what it published and reports it, so you get both or neither. A hard crash or power loss between the two steps can leave the sent record alone (harmless: it only suppresses repeats), and a stray `.kaidah-restore-*` folder or `.kaidah-sent-*` file to delete by hand. `restore` writes the events and the sent record only. It does not restore `kaidah.json` (so a restored log is private by default) or `kaidah.local.json`.

## Format `kaidah-checkpoint-1`

    {
     "format": "kaidah-checkpoint-1",
     "events": { "<eid>": { ...the event file exactly as stored in events/<eid>.json... } },
     "sent": "<the sent file as text, or an empty string>",
     "sha256": "<hex sha256 of the compact, key-sorted JSON of {events, sent}>"
    }

- Event ids are 12 to 16 hex characters. Events are immutable. An event may hold the grant's title, scope, expiry and a reference to the original grant. That is why the file is private and must be encrypted.
- The checksum covers the plain content, so it detects damage and edits after decryption. It is not a signature. The encryption layer must authenticate the ciphertext (an AEAD mode or an authenticated tool).
- The checkpoint adds no timestamp of its own, so the same log and sent record always export to the same bytes.

## Sent record states

One line per record in the sent file. The last line for a key wins.

| Line | State | Meaning |
| --- | --- | --- |
| `KEY` | sent | delivery was confirmed |
| `?KEY` | uncertain | a send was started and its outcome is not known |
| `!KEY` | pending | an attempt was confirmed not delivered, so the notice may be sent again |

`KEY` is `entry:YYYY-MM-DD:phase` with phase `upcoming`, `due` or `expired`, as `kaidah due` prints it.

Order of a delivery by whoever sends (an agent, a scheduler or a person):

1. `kaidah due --format json --sent-file F` and read `notices` and `uncertain`. If `uncertain` is not empty, stop and look at the chat first.
2. `--mark-attempt KEY` BEFORE sending. Then write a checkpoint if you keep one, so a crash after the send cannot lose that the attempt happened.
3. Send. When delivery is confirmed: `--mark-sent KEY`. If it is confirmed that nothing was delivered: `--clear-attempt KEY`. If neither is known, leave it uncertain. An uncertain notice is never listed again as pending.
4. Checkpoint again after the change.

This gives at-least-once delivery with a pause on doubt. It is not exactly-once. A crash between step 3's send and its mark leaves the key uncertain, and a person or agent must settle it, for example by finding the key text in the chat.

## One consistent snapshot, and a check before sending

- `export` and `covers` read the sent file under a shared lock and read the events while holding it. Every append (`--mark-attempt`, `--mark-sent`, `--clear-attempt`) needs the exclusive lock on the same file, so no attempt or delivery can land between the two reads. Events are only added, each by one atomic link, so they are never half written. A caller must not hold its own lock on the sent file while it runs kaidah, because kaidah opens the file again and the two descriptors would wait for each other.
- `covers FILE --sent-file F --key KEY` compares the checksum of the current state with the checksum of FILE, which must be the checkpoint as read back from storage. It exits 1 with STALE if anything changed since (a new event, mark or clear), and also if FILE does not record an attempt (`?KEY`) for KEY. A sender runs it right before sending. If it fails, the attempt is not safely published, so do not send.
- Sequence for one notice, with one owner at a time: `--mark-attempt KEY`, then `export`, then store and read back the encrypted copy and decrypt it, then `covers` on the decrypted copy, then send, then `--mark-sent` (or `--clear-attempt`), then `export` and store again. Mark and checkpoint steps of different notices must not interleave, so one owner runs one notice at a time. If storing fails or `covers` says STALE, stop before sending.
- If the final store after the send fails, the stored copy still shows the attempt as uncertain, so a restore later pauses that notice and does not repeat it. This is the safe side of the gap. The other side, a send that happened and a stored copy older than the attempt, cannot happen when the sequence above is followed. Durable storage ordering is the storage layer's job, and kaidah cannot enforce it. Nothing here is exactly-once.

## Precondition: one owner, no lease

Everything above assumes ONE owner at a time, on one machine, who runs every mark, export, covers and send in sequence. The file lock only orders the local commands. Kaidah has no lease, no cross-machine lock and no way to know that another copy of the log exists. A checkpoint stored somewhere is a copy, and `covers` shows that the copy matched this machine's state when it ran. It does not stop a second machine, a restored older copy or a reset from acting on its own state.

So after any reset or restore, or when more than one machine could be active: do not send automatically. Run `due`, look at every `uncertain` key and the chat by hand, settle them with `--mark-sent` or `--clear-attempt`, and only then resume. Storing the checkpoint with a compare-and-swap on its generation can detect that two owners published, but it does not prevent the second send. Cross-host automation needs a real lease, which kaidah does not provide and this document does not claim.

## Synthetic example

See `tools/checkpoint-example.json`. It holds one made-up grant and one uncertain notice. It is not real data.
