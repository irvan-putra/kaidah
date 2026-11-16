# Practices

These apply whether your assistant is a person or an AI. One example, in practice 13, is marked **(AI-specific)**. Everything else applies to both.

## 1. Say what is true, and say how you know

Ask the assistant to separate what it checked from what it assumes. A good status says what is done, what is still running, what is blocked, and who acts next. "Done" should mean verified, not attempted.

Example: "The page loads" is weaker than "I opened the page signed out and saw the full content."

## 2. Check access from the outside

A link that works for you may not work for others, and the reverse. Verify public or private access from a signed-out view, and compare it with the access setting the service reports. If the two disagree, say so.

## 3. Do not remove a requested feature to make a problem go away

When something is hard, the assistant should explain the real options and the cost of each. Dropping a feature is a decision for the owner. Acceptance of a limitation is not a request to remove the feature.

## 4. Apply a correction everywhere

When you change a decision, the change should reach every place it shows up: the app, the list, the docs, the reminders. Ask for a quick sweep after any correction.

## 5. Do not make the same permission request twice

Once you grant something, such as push access to a repo for a project, it applies only within its stated scope and only while its conditions are met, until it expires or is revoked, whichever comes first. Be clear about all three when you grant it. The assistant should use the grant, name it briefly, and stay inside it. A similar action, a bigger scope or a new audience needs its own grant.

## 6. Keep boundaries on accounts and secrets

Never share passwords or keys in chat. Use the service's own approval or vault flow. Reconnecting an account is not permission to ask for more. Temporary access should have an agreed end, and the assistant should say when it has cleaned up.

## 7. Public repos, with private data kept out

If you want code public, make it public from the start and keep personal data, credentials, device notes and private chat text out of it. Before publishing, scan the code and the history, not only the latest files.

If something slips in:

- Revoke or rotate any exposed secret first.
- Contain it and tell the owner promptly and plainly, including what may still be exposed.
- Rewriting history or removing published builds is the owner's decision. Do it only with approval, never as an implied extra.
- Nobody can guarantee that caches, forks or clones are erased. Say so.

## 8. Reproducible tests

Prefer tests that can be rerun by anyone: documented steps and synthetic fixtures that contain no real people. If a test needs accounts, keep them only when the owner has authorized it, and store their logins securely so a failed run does not lose them. Report what was tested and what was not.

## 9. Work in parallel

If two routes can run at once, run them at once. One stalled investigation should not block another. For a human assistant this is subject to real limits: their capacity, and whether sharing or delegating the work is allowed at all. Handing a route to a colleague needs the owner's approval for both the handoff and any information it carries; parking a route visibly is the fallback, never letting it vanish.

## 10. Give updates during long work

Short, honest progress notes beat silence. Say if work is continuing, blocked or stopped. Do not say "nothing needed from you" when the work is waiting on you.

## 11. Commit identity and links

Use the commit attribution the owner explicitly authorized, check it after pushing, and say how the work was made when that matters. When changes are published, include a link to the commits so the owner can review them.

Commit identity records who committed a change; it does not by itself establish who authored every part or which rights can be licensed. Keep a concise, public-safe provenance note for material human contributions and reused sources. Do not claim exclusive rights merely because code was committed under your name.

## 12. Optional data-sharing features

For optional features that send data somewhere, one owner preference is a simple on/off setting that defaults to off, instead of a confirmation popup on every action. This is a preference, not a rule for every product.

## 13. Match the tool to the job

Prefer simple tools, and the smallest one that does the job, over bigger or more general ones. Question the assumption that the biggest option is needed. This applies to a human assistant choosing between a spreadsheet and a custom system as much as to anyone else.

**(AI-specific)** Example: when an AI assistant builds on-device or automated features, a small task-specific model is often enough, and a large general model is not automatically the right choice.

## 14. Be honest about limits

The assistant should say what it cannot do, what it could not verify, and what it did not finish. Do not claim complete coverage when the check was partial.

## 15. Ask for help before a blocker turns into silent delay

Assistants get blocked: a missing permission, a service that will not respond, a decision nobody has made. A person or an AI can wait too long, hoping it clears. Ask early instead, and keep the request short:

- What is blocked, and since when.
- What help would unblock it, and from whom (the owner, a coworker, a supervisor, or the service's support).
- What can still move in the meantime.

Where the help comes from is the owner's choice. Bringing in a colleague, or telling a third party anything about the work, needs the owner's approval, as in practice 9. If help is not available, say so, park the blocked part visibly, and keep going on the rest. A blocked item should have an agreed time to ask again, so it does not disappear. Check what you can resolve yourself before asking the owner to supply an answer.
