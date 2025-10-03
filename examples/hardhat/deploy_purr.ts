import { ethers } from "hardhat";

async function main(): Promise<void> {
  const [deployer] = await ethers.getSigners();

  console.log("Deploying Purr with account:", await deployer.getAddress());
  console.log("Account balance:", (await deployer.provider!.getBalance(deployer.address)).toString());

  const Purr = await ethers.getContractFactory("Purr");
  const purr = await Purr.deploy();
  await purr.waitForDeployment();

  console.log("Purr deployed to:", await purr.getAddress());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
