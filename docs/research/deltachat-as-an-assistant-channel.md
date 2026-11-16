# Delta Chat as a channel for an assistant: exploration notes

Status: exploration. Source checked 2026-11-16: https://delta.chat/en/help . Wording below follows that page; menu names can differ by platform and app version.

## What the official help says
- Chatmail relays "do not ask for any private data (including no phone numbers)" according to the help page.
- The page says Delta Chat uses push notifications for chatmail profiles where a push service is available, with the device token encrypted before it is stored on the relay. See the page for the exact conditions.
- Delta Chat apps support multiple profiles. The page says "If you have multiple relays, you will receive messages on all of them."
- Relays can be added by QR code or invite link. The page mentions the list at chatmail.at/relays (shown without a scheme on the page; the exact URL has not been opened here).
- Backup, as described for the app at the time: Settings > Chats > Export Backup on the old device, then "I Already Have a Profile" > "Restore from Backup" on the new one. Labels may differ on other platforms or versions.
- Deleting data: the page says that for a single default profile, uninstalling the app triggers deletion of associated address data on the chatmail server, and refers to the relay operator's own page. Conditions apply, so do not generalize.

## Design questions for a bot (not tested)
- Asynchronous use: keep a record of which messages were answered so a restart does not repeat a reply.
- Relay retention and rate limits for bots: not checked.
