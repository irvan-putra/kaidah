# A version-update pattern for a chat-bot-delivered mini app

Status: source reading on 2026-11-12 of a third-party project; re-check before relying on it. Credit: PixelSocial by adbenitez. Sources: https://github.com/ArcaneCircle/pixelsocial and https://github.com/adbenitez/pixelsocial-bot

## Pattern observed
- The bot ships the mini-app file (.xdc) inside its own package and hardcodes the app version it carries.
- Updating the app means releasing a new bot package with the new file and version value. No in-chat publish command was found.
- The version check is per instance: when a status update arrives from the app copy the bot itself sent, the bot reads the version in the app's manifest and, if it differs from its own, re-sends the current app.

## Why it matters
It is one way to keep distributed mini-apps current without a central store. The tradeoff is that updates depend on the bot being released and running.
