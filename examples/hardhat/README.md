# Hardhat Examples

This directory contains Hardhat scripts that complement the Python examples in this repository.

## `deploy_purr.ts`

A minimal deployment helper that deploys the sample `Purr` ERC-20 contract used in the Python examples.

### Prerequisites

- Node.js 18+
- Hardhat with the Ethers plugin (`npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox`)
- The `Purr` contract compiled by Hardhat (include it in your Hardhat project under `contracts/Purr.sol`)

### Usage

1. Copy the script into your Hardhat project's `scripts/` directory or execute it directly with `npx hardhat run`.
2. Configure your network and private key in `hardhat.config.ts` or via environment variables.
3. Deploy:

   ```bash
   npx hardhat run --network <network> scripts/deploy_purr.ts
   ```

The script logs the deployer address, its current balance, and the deployed contract address once deployment completes.
