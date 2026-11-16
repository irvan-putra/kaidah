# Delta Chat core: system messages name the contact by display name

Status: chatmail core tag v2.69.0 source read 2026-11-16. Source reading only.

In `src/stock_str.rs`, `get_stock_name` is documented as: "Get contact name, e.g. `Bob`, or `bob@example.net` if no name is set", and returns `contact.get_display_name()`. Group-management stock strings (for example "added by X") fill their placeholder with that value.
https://raw.githubusercontent.com/chatmail/core/v2.69.0/src/stock_str.rs

Implication (reasoning, not a source claim): the rendered name is a display label. It is not shown here to be an authenticated or stable identifier, and who controls a contact's display name was not checked. Code that needs to know who acted should use the message's structured sender or contact id rather than matching on rendered text.
