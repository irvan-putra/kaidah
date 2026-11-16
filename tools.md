# Tools that could help

Status: exploratory proposals. Nothing here is built or committed to. The question is what would help a human assistant keep up with fast, parallel work - and, more broadly, how an owner and an assistant coordinate shared work so both always know where it stands.

## Why tools at all

An assistant, human or AI, juggles many threads: permissions granted, work in flight, decisions made in passing. Nobody should have to hold all of that in their head, and chat history is a bad place to look it up. A few shared records do the remembering, so owner and assistant coordinate from the same page instead of relying on either side's memory.

## Proposal 1: a shared decision and permission log

One place, visible to both the owner and the assistant, that records:

- **Agreed**: decisions and grants, with their scope, conditions and expiry ("push access to repo X for project Y, until date Z").
- **Waiting**: what is blocked, and on whom.
- **Needs approval**: what the assistant wants to do next and cannot start without a yes.

Format ideas: a shared note, a spreadsheet, or a small app. The format matters less than the habit: the assistant writes to it, the owner can check it any time, and both treat it as the index of what was agreed. When a grant expires or a decision changes, the log changes in the same sweep (see practice 4).

Two rules keep the log honest:

- **It is an index, not authority.** Each entry links back to the original evidence of the decision or grant - the message or document where it was actually agreed. A summary written by the assistant does not create a permission or widen one; if the entry and the original disagree, the original wins and the entry gets fixed.
- **Corrections are visible.** A wrong or stale entry is corrected in a way that keeps the relevant history, so both sides can see what changed and when, not just the latest state.

What it is not: a way to watch or score the assistant. It records decisions and state, not messages, keystrokes or time spent.

## Proposal 2: a standing status page

A single page that always answers: what is running, what finished, what is blocked, and who acts next. The same information a good progress update carries (practice 10), but current at any hour, not only when a message arrives.

## Proposal 3: templates for repeated grants

If the same kind of permission comes up often - for example, push access to a new repo for a new project - a short template (scope, conditions, expiry) turns granting it into a one-line decision instead of a fresh negotiation each time (practice 5).

## Open questions

- Where should the log live so both sides actually keep it updated?
- How much detail is useful before it becomes noise?
- Who cleans up expired grants, and how does the log show that it happened?

Suggestions and experiments are welcome as issues or pull requests.
