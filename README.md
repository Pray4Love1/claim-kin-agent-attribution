# hyperliquid-python-sdk

<div align="center">

[![Dependencies Status](https://img.shields.io/badge/dependencies-up%20to%20date-brightgreen.svg)](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/pulls?utf8=%E2%9C%93&q=is%3Apr%20author%3Aapp%2Fdependabot)
[![Attribution Test](https://github.com/Pray4Love1/claim-kin-agent-attribution/actions/workflows/attribution-test.yml/badge.svg)](https://github.com/Pray4Love1/claim-kin-agent-attribution/actions/workflows/attribution-test.yml)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Security: bandit](https://img.shields.io/badge/security-bandit-green.svg)](https://github.com/PyCQA/bandit)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/master/.pre-commit-config.yaml)
[![Semantic Versions](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--versions-e10079.svg)](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/releases)
[![License](https://img.shields.io/pypi/l/hyperliquid-python-sdk)](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/master/LICENSE.md)

SDK for Hyperliquid API trading with Python.

</div>

## Installation
```bash
pip install hyperliquid-python-sdk
```
## Configuration 

- Set the public key as the `account_address` in examples/config.json.
- Set your private key as the `secret_key` in examples/config.json.
- See the example of loading the config in examples/example_utils.py

### [Optional] Generate a new API key for an API Wallet
Generate and authorize a new API private key on https://app.hyperliquid.xyz/API, and set the API wallet's private key as the `secret_key` in examples/config.json. Note that you must still set the public key of the main wallet *not* the API wallet as the `account_address` in examples/config.json

## Usage Examples
```python
from hyperliquid.info import Info
from hyperliquid.utils import constants

info = Info(constants.TESTNET_API_URL, skip_ws=True)
user_state = info.user_state("0xcd5051944f780a621ee62e39e493c489668acf4d")
print(user_state)
```
See [examples](examples) for more complete examples. You can also checkout the repo and run any of the examples after configuring your private key e.g.
```bash
cp examples/config.json.example examples/config.json
vim examples/config.json
python examples/basic_order.py
```

### 🔁 Codex Withdrawal Helper

This script lets you trigger a withdrawal of USDC (or any supported token) from your Hyperliquid sub-account using the Codex API wallet. By default it bridges funds to the Codex wallet address:

```
0x996994D2914DF4eEE6176FD5eE152e2922787EE7
```

You can override the destination at runtime.

#### 🔧 Setup

Set the following environment variables (for example via a local `.env` or Codespaces secrets):

```env
HL_API_KEY=your_codex_api_private_key
CODEX_DEFAULT_DESTINATION=0x996994D2914DF4eEE6176FD5eE152e2922787EE7
HL_API_URL=https://api.hyperliquid.xyz
```

#### 🚀 Usage

```bash
python scripts/codex_trigger_hyperliquid_withdrawal.py --amount 1000000
```

This submits a withdrawal of `1,000,000` base units of USDC (~$1M) from the configured account.

#### 🧩 Optional arguments

| Flag | Description |
| --- | --- |
| `--amount` | **Required.** Amount to withdraw (base units, e.g. 1000000 for $1M). |
| `--destination` | Override the recipient wallet; defaults to the Codex EE7 address. |
| `--account` | Withdraw from a specific Hyperliquid account or sub-account (e.g. `027`). |
| `--base-url` | Override the Hyperliquid API base URL (defaults to mainnet when unset). |
| `--json` | Emit the raw JSON response for scripting or pipelines. |

#### 🧪 Example

```bash
python scripts/codex_trigger_hyperliquid_withdrawal.py \
  --amount 5000000 \
  --destination 0xYourCustomAddress \
  --account 027 \
  --json
```

Example output:

```json
{
  "status": "ok",
  "amount": 5000000,
  "destination": "0xYourCustomAddress",
  "txHash": "0x..."
}
```

#### 🧠 Notes

- Sub-account `027` maps to the Codex API wallet flow and is fully supported.
- The destination defaults to the Codex EE7 wallet unless you pass `--destination`.
- There is no dry-run mode—the command submits a real withdrawal as soon as it runs.
- The helper must be executed manually from your environment; this project will never trigger it automatically on your behalf.
- Inputs are validated for formatting and balance sufficiency before submission.
- Monitor withdrawals on https://app.hyperliquid.xyz or the corresponding block explorer.

## Getting started with contributing to this repo

1. Download `Poetry`: https://python-poetry.org/. 
   - Note that in the install script you might have to set `symlinks=True` in `venv.EnvBuilder`.
   - Note that Poetry v2 is not supported, so you'll need to specify a specific version e.g. curl -sSL https://install.python-poetry.org | POETRY_VERSION=1.4.1 python3 - 

2. Point poetry to correct version of python. For development we require python 3.10 exactly. Some dependencies have issues on 3.11, while older versions don't have correct typing support.
`brew install python@3.10 && poetry env use /opt/homebrew/Cellar/python@3.10/3.10.16/bin/python3.10`

3. Install dependencies:

```bash
make install
```

### Makefile usage

CLI commands for faster development. See `make help` for more details.

```bash
check-safety          Run safety checks on dependencies
cleanup               Cleanup project
install               Install dependencies from poetry.lock
install-types         Find and install additional types for mypy
lint                  Alias for the pre-commit target
lockfile-update       Update poetry.lock
lockfile-update-full  Fully regenerate poetry.lock
poetry-download       Download and install poetry
pre-commit            Run linters + formatters via pre-commit, run "make pre-commit hook=black" to run only black
test                  Run tests with pytest
update-dev-deps       Update development dependencies to latest versions
```

## Releases

You can see the list of available releases on the [GitHub Releases](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/releases) page.

We follow the [Semantic Versions](https://semver.org/) specification and use [`Release Drafter`](https://github.com/marketplace/actions/release-drafter). As pull requests are merged, a draft release is kept up-to-date listing the changes, ready to publish when you’re ready. With the categories option, you can categorize pull requests in release notes using labels.

### List of labels and corresponding titles

|               **Label**               |  **Title in Releases**  |
| :-----------------------------------: | :---------------------: |
|       `enhancement`, `feature`        |        Features         |
| `bug`, `refactoring`, `bugfix`, `fix` |  Fixes & Refactoring    |
|       `build`, `ci`, `testing`        |  Build System & CI/CD   |
|              `breaking`               |    Breaking Changes     |
|            `documentation`            |     Documentation       |
|            `dependencies`             |  Dependencies updates   |

### Building and releasing

Building a new version of the application contains steps:

- Bump the version of your package with `poetry version <version>`. You can pass the new version explicitly, or a rule such as `major`, `minor`, or `patch`. For more details, refer to the [Semantic Versions](https://semver.org/) standard.
- Make a commit to `GitHub`
- Create a `GitHub release`
- `poetry publish --build`

## License

This project is licensed under the terms of the `MIT` license. See [LICENSE](LICENSE.md) for more details.

```bibtex
@misc{hyperliquid-python-sdk,
  author = {Hyperliquid},
  title = {SDK for Hyperliquid API trading with Python.},
  year = {2024},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/hyperliquid-dex/hyperliquid-python-sdk}}
}
```

## Credits

This project was generated with [`python-package-template`](https://github.com/TezRomacH/python-package-template).
