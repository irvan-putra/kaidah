# Delta Chat: key management, as the official FAQ states it

Status: Delta Chat FAQ read 2026-11-16 (https://delta.chat/en/help), the section "Can I reuse my existing private key?". Nothing was tested. Moving a profile between devices is already covered in the existing second-device notes, so it is not repeated.

## What the FAQ says
- Asked "Can I reuse my existing private key?", it answers "No."
- It says: "Delta Chat generates secure OpenPGP keys according to the Autocrypt specification 1.1. We do not recommend or offer users to perform manual key management."
- It names one route for extracting a key, called an expert method: "you need to look it up in the 'keypairs' SQLite table of a profile backup tar-file."
- In the preceding encryption-status section, it describes a manual check in the "Encryption Info" dialog, which shows two fingerprints, and says: "If the same fingerprints appear on your own and your contact's device, the connection is safe." This is the FAQ's wording for that manual fingerprint comparison; this note does not assess what it does or does not protect against.

## What this implies (reasoning, not a source claim)
A key-only export is not described as a supported feature in this FAQ; the documented extraction route is reading a full profile backup. Anyone planning a second client for an existing address should check the current docs on what a new key means for existing contacts. That was not verified here.
