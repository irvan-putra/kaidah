# Public log

A public, curated log of decisions, grants and status, kept with [pandu](https://github.com/irvan-putra/pandu).

Entries here are written for public readers. Nothing private is recorded here, and nothing is imported from private conversations. Each entry is a small immutable file in `events/`; corrections and closures are new files, so history stays visible. The log is an index, not authority: linked evidence wins if they disagree.

A scheduled job records expired grants once a day. That only records the expiry in the log. It does not remove any access anywhere.

To read the current state, check out the repository and run `python3 tools/pandu.py status` from a copy of the pandu code with `PANDU_DIR` pointing here.
