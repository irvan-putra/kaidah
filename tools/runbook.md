# Runbook: expiry notices with a private log

For one person or one program that runs the notices for one owner. Read `checkpoint.md` first. This is a manual routine. Nothing here runs by itself, and pandu has no lease, so only one runner may be active at a time.

`tests/rehearsal.py` runs scripted local commands from a small simulated caller that follows the steps below, using made-up data in temporary folders, a fake chat file and a fake store (numbered copies). It is evidence that the pandu commands behave as described when called in this order. It is not proof of any real send, real storage or encryption, a real chat, or two machines running at once. It sends nothing. Run it after any change to the commands.

## Before you start

- One runner, on one machine. If another machine or copy might be active, stop.
- Know where the latest checkpoint is stored, and which copy is the newest. Restoring an older copy is the one case the tool cannot catch (see "Known gap").
- Keep the log, the sent file and temporary plain checkpoints in a private folder, and delete plain checkpoints after use.

## Each time a notice is due

1. Save a text export of the chat to a file CHAT (for example the last few weeks). `pandu due --format json --sent-file SENT --seen-in CHAT`. If `uncertain` is not empty, stop and settle those first (below). A key whose `(ref KEY)` appears in CHAT but is not recorded as sent is listed there, never as a pending notice.
2. For each key held because its text is in the chat: do not send. Do NOT mark it sent from the text alone, because the text may be a draft, a quote or a paste that was never delivered. Decide by hand. Only when you have real evidence of delivery (the sent message itself, not a copy of its words), record `--mark-sent KEY`. If you cannot tell, leave it held. The cost is that a match which was not a delivery holds that notice until someone decides, so a notice can wait. That is the safe side. To release a draft false match, take that text out of the export file, since `--seen-in` only reads the file.
3. `pandu due --sent-file SENT --mark-attempt KEY`.
4. `pandu checkpoint export FILE --sent-file SENT`, store it, read the stored copy back and decrypt it if it is encrypted.
5. `pandu checkpoint covers STORED_COPY --sent-file SENT --key KEY`. If it fails (STALE or no attempt), do not send. Go back to step 4.
6. Send the notice, using the `message` text unchanged so the key is in it.
7. Delivery confirmed: `--mark-sent KEY`. Confirmed that nothing was delivered: `--clear-attempt KEY`. Unknown: change nothing, so the key stays uncertain.
8. Export and store again. Write down the witness number now: `pandu checkpoint verify FILE` prints the number of sent record lines. Keep that one number somewhere that is not the stored copy (see below).

## Keep a witness

Within one history the sent record only grows, so its line count never goes down. A restore from an older copy of the same history has fewer lines than the count you wrote down at the last publish. Pandu cannot know that count, so the runner keeps it outside the stored copy (any small private note that survives a reset of the store, for example a reminder or a line in a notebook). The number is not secret. It is only useful if it is saved after each publish, and only if it is fresh. It checks one thing: that the copy has at least that many lines. A copy from a different or divergent history with the same or a larger count passes, because the check looks at the number and not at the content. A witness that is older than the last publish lets an older copy through too. It is a guard against an old copy of the same log, not proof that a copy is the right one. An optional extra, a hash prefix of the first lines to tie the witness to one history, is a proposal and is not built. Where it lives is the owner's choice, and pandu does not hold it.

## After a reset or restore

1. Do not send anything yet.
2. Restore the NEWEST stored checkpoint: `pandu checkpoint restore FILE --into NEWDIR --sent-file NEWSENT --min-records N`, where N is the witness number you wrote down at the last publish (see "Keep a witness"). A copy with fewer sent record lines than N is refused. If you cannot tell which copy is newest and have no witness, stop.
3. `pandu due --format json --sent-file NEWSENT --seen-in CHAT`. Every `uncertain` key: look in the chat for its `(ref KEY)`. Found, and you have real evidence that it was delivered: `--mark-sent KEY`. Found only as text that may be a draft or a quote, or not found and not sure: leave it uncertain. Not found and you are sure nothing was sent: `--clear-attempt KEY`.
4. Only then run the normal routine.

## What the rehearsal showed

All 21 checks pass. Each case has its own made-up grant, key, chat file, sent file and store.

| Case | Result |
| --- | --- |
| A: normal delivery | The notice is listed once and sent once. The latest stored copy restores to nothing pending or uncertain, and a second run does nothing. |
| B1: nothing stored. B2: only an old copy stored, taken before the attempt | `covers` fails, so the caller does not send. |
| M1, M2: the same B cases through a caller that ignores the `covers` exit | The caller does send. This shows the B checks are not empty. |
| C: crash after the send and before `--mark-sent`, then a reset | After restore the key is uncertain, never pending, and a run on the restored state sends nothing. It is settled by hand after delivery is verified. |
| D1: restore a copy older than the attempt, and the key text is still in the chat | `--seen-in` holds the key as uncertain. The caller stops and sends nothing, and no delivery is recorded. |
| M3: the same case through a caller that skips `--seen-in` | It sends again. This shows the D1 check is not empty. |
| D2: the same restore, but the chat history is lost and no witness is kept | **Known gap.** The caller sends the notice again. |
| D3: the same restore, chat lost, but the witness number was kept | The restore of the older copy is refused. The newest copy restores and nothing is pending. |
| E: the chat holds the key text as an undelivered draft | The caller stops and records nothing. The key is held, not marked sent. |
| F: sent, but delivery is not verified | The key stays uncertain. |
| G: restore without `--sent-file`, into a non-empty folder, or from an edited checkpoint | Refused. |

## What is still open

A stale restore is caught when the chat export still shows the key (`--seen-in`), or when the runner kept a fresh witness number (`--min-records`) and the older copy has fewer lines. Limits of each:

- `--seen-in` only sees a `(ref KEY)` that is exactly as the notice wrote it: one line, the key in lowercase hex, unchanged. An export that wraps the line, escapes characters, changes spaces (for example non-breaking spaces), or is empty or cut off can miss it. Not finding a match does not show that the notice was not sent.
- `--min-records` compares line counts only (see "Keep a witness").

It is NOT caught when both the chat history and a fresh witness are gone. Then nothing in reach shows that the notice was sent, and a resend can happen. No pandu command can fix that. It needs a second record that survives separately from the stored copy and the chat, and choosing where that lives is an owner decision (the witness note above is the smallest form of it). The rehearsal shows the commands behave this way. It does not show that any real chat export, store or note survives a reset.

Other proposals, not built:

1. The storage layer should refuse to hand back anything but the newest copy and record a generation number. This belongs to the caller.
2. `pandu due --strict`: exit with a non-zero code when `uncertain` is not empty, so a caller cannot ignore it.

No real send, account or revocation is part of this document. It checks that the local record and checkpoint steps behave. It is not an autonomous system.
