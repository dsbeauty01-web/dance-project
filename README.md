# dance-project

[![Nova Laws](https://github.com/dsbeauty01-web/dance-project/actions/workflows/laws.yml/badge.svg)](https://github.com/dsbeauty01-web/dance-project/actions/workflows/laws.yml)

Nova Dance — a browser dance game for kids, with a live AI avatar.

## Before you touch anything

Read **[START-HERE-CLI.md](START-HERE-CLI.md)**. This repo enforces its hard-won
fixes as **walls**: [LAWS.md](LAWS.md) is an append-only registry of laws, each
with a marker the CI greps on every push. If an ACTIVE law's marker vanishes,
the build goes **RED** with the law's name. Restore the law — never delete the
test.

Run the walls locally before you push:

```bash
bash tools/laws/run-all.sh
```
