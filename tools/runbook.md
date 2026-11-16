# Runbook: expiry notices with a private log

For one person or one program that runs the notices for one owner. Read `checkpoint.md` first. This is a manual routine. Nothing here runs by itself, and pandu has no lease, so only one runner may be active at a time.

`tests/rehearsal.py` runs scripted local commands from a small simulated caller that follows the steps below, using made-up data in temporary folders, a fake chat file and a fake store (numbered copies). It is evidence that the pandu commands behave as described when called in this order. It is not proof of any real send, real storage or encryption, a real chat, or two machines running at once. It sends nothing. Run it after any change to the commands.

## Before you start

- One runner, on one machine. If another machine or copy might be active, stop.
- Know where the latest checkpoint is stored, and which copy is the newest. Restoring an older copy is the one case the tool cannot catch (see "Known gap").
- Keep the log, the sent file and temporary plain checkpoints in a private folder, and delete plain checkpoints after use.

## Each time a notice is due

1. `pandu due --format json --sent-file SENT`. If `uncertain` is not empty, stop and settle those first (below).
2. For each notice, search the chat for its key text, `(ref KEY)`. If it is there, do not send. Do NOT mark it sent from the text alone: the text may be a draft, a quote, or a paste that was never delivered. Leave the key uncertain (`--mark-attempt KEY` if it is not already) and decide by hand. Only when you have real evidence of delivery (the sent message itself, not a copy of its words), record `--mark-sent KEY`. If you cannot tell, leave it uncertain. The cost of this caution is that a match which was not a delivery holds that notice until someone decides, so a notice can wait. That is the safe side.
3. `pandu due --sent-file SENT --mark-attempt KEY`.
4. `pandu checkpoint export FILE --sent-file SENT`, store it, read the stored copy back and decrypt it if it is encrypted.
5. `pandu checkpoint covers STORED_COPY --sent-file SENT --key KEY`. If it fails (STALE or no attempt), do not send. Go back to step 4.
6. Send the notice, using the `message` text unchanged so the key is in it.
7. Delivery confirmed: `--mark-sent KEY`. Confirmed that nothing was delivered: `--clear-attempt KEY`. Unknown: change nothing, so the key stays uncertain.
8. Export and store again.

## After a reset or restore

1. Do not send anything yet.
2. Restore the NEWEST stored checkpoint: `pandu checkpoint restore FILE --into NEWDIR --sent-file NEWSENT`. If you cannot tell which copy is newest, stop.
3. `pandu due --format json --sent-file NEWSENT`. Every `uncertain` key: search the chat for its `(ref KEY)`. Found, and you have real evidence that it was delivered: `--mark-sent KEY`. Found only as text that may be a draft or a quote, or not found and not sure: leave it uncertain. Not found and you are sure nothing was sent: `--clear-attempt KEY`.
4. Only then run the normal routine.

## What the rehearsal showed

All 18 checks pass. Each case has its own made-up grant, key, chat file, sent file and store.

| Case | Result |
| --- | --- |
| A: normal delivery | The notice is listed once and sent once. The latest stored copy restores to nothing pending or uncertain, and a second run does nothing. |
| B1: nothing stored. B2: only an old copy stored, taken before the attempt | `covers` fails, so the caller does not send. |
| M1, M2: the same B cases through a caller that ignores the `covers` exit | The caller does send. This shows the B checks are not empty. |
| C: crash after the send and before `--mark-sent`, then a reset | After restore the key is uncertain, never pending, and a run on the restored state sends nothing. It is settled by hand after delivery is verified. |
| D1: restore a copy older than the attempt, and the key text is still in the chat | The caller stops and sends nothing. The key stays uncertain and is not marked sent. |
| D2: the same restore, but the chat history is lost | **Known gap.** The caller sends the notice again. |
| E: the chat holds the key text as an undelivered draft | The caller stops and leaves the key uncertain. It does not mark it sent. |
| F: sent, but delivery is not verified | The key stays uncertain. |
| G: restore without `--sent-file`, into a non-empty folder, or from an edited checkpoint | Refused. |

## Known gap and proposals

Restoring a copy that is older than a send brings back an old sent record, so a sent notice looks pending. Pandu cannot see which copy is newest. For now the chat search in step 2 is the only protection, and it is manual. It fails if the chat history is lost (case D2) and it can hold a notice back wrongly if the match was only a draft (case E).

Proposals, not built:

1. `pandu due --seen-in FILE`: treat a key whose `(ref KEY)` appears in a text export of the chat as uncertain, not pending, never as sent. This makes step 2 automatic and fails on the safe side. It still depends on the chat history being there, and it can hold a notice back for a draft match.
2. The storage layer should refuse to hand back anything but the newest copy, and should record a generation number. Pandu does not know about generations, so this belongs to the caller.
3. `pandu due --strict`: exit with a non-zero code when `uncertain` is not empty, so a caller cannot ignore it.

No real send, account or revocation is part of this document. It checks that the local record and checkpoint steps behave. It is not an autonomous system.
