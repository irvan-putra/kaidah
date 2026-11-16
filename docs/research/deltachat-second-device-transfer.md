# Delta Chat "Add Second Device": what the code and docs say

Status: source reading, re-checked 2026-11-16 against the main branch of chatmail core (earlier reading: v2.69.0). Not run end to end. Behavior can change between versions.

## What the source says
- The module describes a Provider (starts a server) and a Getter (connects and retrieves). The provider shows a QR code; the getter scans it and presents the token it contains, which the provider checks. The QR also carries the provider's peer ID and addresses. The source was read for these two mechanisms (peer ID, token). Whether they prevent impersonation was not audited here, and anyone who captures the QR code may obtain the token, so treat that as a possible risk. https://raw.githubusercontent.com/chatmail/core/main/src/imex/transfer.rs
- Both endpoints are built with `RelayMode::Disabled` in that file. iroh's documentation lists Disabled as a relay mode option. https://docs.rs/iroh/latest/iroh/endpoint/enum.RelayMode.html
- The QR scheme in qr.rs on main is a `DCBACKUP` prefix with a version constant (5 when read); an older reading of the exact text format was not re-verified, so it is not reproduced here. https://raw.githubusercontent.com/chatmail/core/main/src/qr.rs
- The official help describes using the feature between devices and says to be on the same network. https://delta.chat/en/help

## What this implies (reasoning, not tested)
With relays disabled the connection depends on the getter reaching one of the provider's listed direct addresses. That is usually possible on the same local network. Whether it can work across networks depends on whether those addresses are reachable (for example public addresses or port forwarding); this note did not test it and does not claim it is impossible.

## Backups
Upstream issue 7743 (open, last updated 2026-01-26) states that backups written to a file are unencrypted and proposes encryption. https://github.com/chatmail/core/issues/7743 Check the version in use, since this may have changed.

## Handling
Treat the QR text as a credential while a transfer is offered, and avoid posting it in chats or screenshots.
