const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const EventChain = await hre.ethers.getContractFactory("EventChain");
  const contract = await EventChain.deploy();
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  const artifact = await hre.artifacts.readArtifact("EventChain");
  const network = await hre.ethers.provider.getNetwork();

  const deployment = {
    contractName: "EventChain",
    address,
    chainId: Number(network.chainId),
    networkName: hre.network.name,
    rpcUrl: "http://127.0.0.1:8545",
    abi: artifact.abi,
    deployedAt: new Date().toISOString()
  };

  const outputDir = path.join(__dirname, "..", "blockchain");
  fs.mkdirSync(outputDir, { recursive: true });
  fs.writeFileSync(
    path.join(outputDir, "deployment.json"),
    JSON.stringify(deployment, null, 2)
  );

  console.log(`EventChain deployed to: ${address}`);
  console.log("Deployment data written to blockchain/deployment.json");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
