 Codex Phantom Bot Guide

This guide documents the Codex phantom bot helper that accompanies the
Hyperliquid attribution toolkit.  It covers the setup script, day-to-day
operation, and container maintenance practices so the bot keeps running
reliably.

## Overview

The phantom bot is a thin orchestration layer around the Hyperliquid
EIP-712 phantom agent workflow.  It derives the connection ID for an
unsigned action, exports the typed data required by external signers, and
stores metadata such as the nonce, vault address, and expiry for auditing
purposes.

Key files introduced for the bot:

- `hyperliquid/utils/phantom_bot.py` – reusable helpers for computing phantom
  agent payloads and JSON summaries.
- `scripts/codex_phantom_bot.py` – CLI entry point that reads an action payload
  and prints a ready-to-sign summary.
- `scripts/setup_codex_phantom_bot.sh` – idempotent setup script that
  provisions Python/Node dependencies and (optionally) prepares an environment
  template.

## Setup

1. Ensure the repository dependencies are available on the host.  The setup
   script expects Python 3.10+, `pip`, and (optionally) `npm` when the
   JavaScript tooling is required.
2. Run the setup helper:

   ```bash
   scripts/setup_codex_phantom_bot.sh --env-file codex_phantom.env
   ```

   - The `--env-file` flag generates a template with placeholders for the
     Hyperliquid API URL, signing key, and default vault controller.  Store the
     filled version securely (do **not** commit secrets).
   - Use `--python` if a specific interpreter is required, and `--force-reinstall`
     to refresh dependencies after an upgrade.
3. Activate the virtual environment before invoking the CLI:

   ```bash
   source .venv/codex-phantom/bin/activate
   ```

## Generating Phantom Sessions

Prepare an action payload using existing helpers (for example, the exchange
client’s `bulk_orders_tx`).  Pipe the payload into the CLI to generate the
phantom session summary:

```bash
python scripts/codex_phantom_bot.py --mainnet --pretty < action.json > phantom_session.json
```

Useful flags:

- `--nonce` and `--expires-after` override the timestamp defaults.
- `--dump-typed-data typed.json` writes the EIP-712 typed data to a separate
  file, keeping the summary lightweight.
- `--no-action` or `--no-typed-data` trim the output when an external system
  only needs the connection ID or metadata.

## Container Maintenance

When running inside a long-lived container, adopt the following routines:

- **Dependency refresh:** Re-run `scripts/setup_codex_phantom_bot.sh --force-reinstall`
  during image rebuilds to pick up Python package upgrades and regenerate the
  virtual environment deterministically.
- **Health checks:** Schedule a cron job (or container health command) that
  executes `python scripts/codex_phantom_bot.py --help`.  A non-zero exit code
  indicates the environment is missing dependencies or the CLI cannot be
  imported.
- **Log hygiene:** Redirect CLI output to structured log files (e.g.
  `/var/log/codex_phantom/`) and rotate them regularly with `logrotate` or the
  container runtime’s logging driver.
- **Secrets management:** Mount the environment file as a read-only volume and
  rotate the signing key periodically.  After rotation, regenerate summaries to
  ensure the phantom connection IDs reflect the active credentials.
- **Backups:** Persist generated session summaries or typed data to durable
  storage so action audits survive container restarts.

Following these steps ensures the Codex phantom bot remains reproducible,
traceable, and ready for production workflows.
