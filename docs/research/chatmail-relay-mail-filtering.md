# Does a chatmail relay accept plain email from outside?

Status: documentation reading on 2026-11-16 (first read 2026-11-12). Not tested. Behavior depends on the relay and its version and settings.

## What the docs say
- The filtermail README says it enforces mandatory end-to-end encryption, and rejects incoming messages unless they meet at least one listed criterion. Criteria seen include: the message is PGP encrypted, or all recipients allow cleartext. https://github.com/chatmail/filtermail
- The relay pull request "Reject unencrypted incoming mail" describes an `enforceE2EE` file that is checked per recipient. https://github.com/chatmail/relay/pull/538
- The public relay nine.testrun.org describes its policy on its info page; its wording about direction is imprecise. https://www.nine.testrun.org/info.html

## Reading
A plain unencrypted email from an ordinary mailbox is likely to be rejected by a relay that enforces encryption for the recipient. An encrypted message (PGP) is one listed way through the filter. Whether a contact-setup (secure-join) exchange is by itself enough for a relay to admit later mail was not established here; filtermail's list of criteria is the thing to read. Check the target relay's configuration.
