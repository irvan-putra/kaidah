# Delta Chat on Android: which links open the app, and what a setup-contact invite looks like

Status: official source read 2026-11-16 (deltachat-android `main` at commit 228861a5920a, and chatmail core tag v2.69.0). Source reading only; nothing was installed or run. Intent filters declare what the app can receive; they do not show what happens after the link opens.

## Links the Android app declares it can open
In `src/main/AndroidManifest.xml`, `RoutingActivity` (exported) declares VIEW, DEFAULT, BROWSABLE intent filters for:
- the scheme `openpgp4fpr`, with extra case variants (`OPENPGP4FPR`, `OpenPGP4FPR`, `OpenPGP4Fpr`, `OpenPGP4fpr`) and the comment "Android's scheme matcher is case-sensitive, so include most likely variations";
- `https` with host `i.delta.chat`, marked `android:autoVerify="true"`. Whether verification succeeds on a given device was not checked.
Another activity declares schemes `dcaccount` and `dclogin` (also in case variants).
https://raw.githubusercontent.com/deltachat/deltachat-android/main/src/main/AndroidManifest.xml

## What the core generates for a setup-contact invite
In chatmail core v2.69.0 `src/securejoin.rs`, the generated invite text is an `https://i.delta.chat/#<fingerprint>&v=3&i=<invitenumber>&s=<auth>&a=<address>...&n=<name>` URL (group and broadcast variants use further parameters). It is not an `openpgp4fpr:` string in this version.
https://raw.githubusercontent.com/chatmail/core/v2.69.0/src/securejoin.rs

## Implication (reasoning, not a source claim)
A program that wants to hand an invite to the installed Delta Chat app on the same phone could fire an ACTION_VIEW intent with that URL, since the manifest declares a matching filter. How the app then handles it, and whether a given version behaves the same, was not tested.
