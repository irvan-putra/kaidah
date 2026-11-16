# What one public chatmail relay says about message retention and account deletion

Status: pages read 2026-11-16. This covers one relay (nine.testrun.org) only. Other relays set their own rules, and no other relay's policy was read. Policies can change; check the relay's own pages.

## nine.testrun.org
From its info page (https://nine.testrun.org/info.html):
- "Messages are unconditionally removed latest 20 days after arriving on the server. Earlier, if storage may exceed otherwise."
- "You may send up to 60 messages per minute."
- "You can store up to 700M messages on the server." (the page's wording; the unit is as written there, and "M" may mean megabytes rather than a message count, which was not clarified)
- "Un-encrypted messages are blocked to recipients outside nine.testrun.org but setting up contact via QR invite codes allows your messages to pass freely to any outside recipients."
- Account deletion: "If you remove a nine.testrun.org profile from within the Delta Chat app, then the according account on the server, along with all associated data, is automatically deleted 100 days afterwards."

From its privacy page (https://nine.testrun.org/privacy.html):
- The server "neither asks for nor retains personal information" and "unconditionally removes messages after 20 days."
- The page also says mail is stored for the recipient "until explicitly deleted by the user or until a fixed time period is exceeded, (usually 4-8 weeks)", which differs from the 20-day figure on the same page set; the stricter 20-day statement is the one repeated on both pages, and the discrepancy was not resolved here.
- "We will keep logs of messages in transit for a limited time", used for debugging delivery problems.

## Choosing a relay
The chatmail relay directory (https://chatmail.at/relays) lists many relays run by different groups, says nine.testrun.org is "the default onboarding relay for many chatmail apps", and gives each relay's hosting country. It states no retention figures, so a relay's own info page is where to look.

## What this means for an app built on chatmail
The relay states a maximum 20-day retention, although its privacy text also contains unresolved 4-8 week wording. Do not rely on relay storage as a history backup; keep and test independent local history/backups. Exact restoration design was not researched here.
