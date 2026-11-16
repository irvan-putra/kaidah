# Delta Chat key changes and old-message readability: open questions

Status: UNVERIFIED research questions, recorded 16 November 2026. This note does not establish how any current Delta Chat client behaves. No reproduction test accompanies it.

## Questions still open

- After a profile starts using a different encryption key, what does an existing contact see? Does this differ for verified and unverified contacts, and across client versions?
- When an existing email address is used to set up a new profile without restoring the original profile, which previously received encrypted messages, if any, can that new profile read?
- How does that differ from reading messages already stored in the original profile, restoring a full backup, or using the documented second-device transfer?

Do not treat these questions as findings that a warning always appears or that all old messages become unreadable. Both would require evidence with the setup and versions stated.

## Evidence needed

A useful follow-up would record exact client and core versions, distinguish a new profile from a restored profile, and use only disposable accounts and synthetic messages. Check both contacts' views and separate locally stored message history from encrypted messages fetched again from a server. Compare verified and unverified contacts. Source-code evidence should identify a pinned revision and the relevant code paths, not rely on keyword-search absence.

## Starting points, not proof of an answer

- [Delta Chat help](https://delta.chat/en/help)
- [chatmail core source](https://github.com/chatmail/core)

Publication of this note records an unresolved question. It is not advice to replace keys, recreate a profile, or discard a backup.
