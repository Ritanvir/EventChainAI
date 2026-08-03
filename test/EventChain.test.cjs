const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("EventChain", function () {
  async function deployFixture() {
    const [organizer, attendee, sponsor, vendor] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("EventChain");
    const contract = await Factory.deploy();
    await contract.waitForDeployment();
    return { contract, organizer, attendee, sponsor, vendor };
  }

  it("creates an event and mints an NFT ticket", async function () {
    const { contract, organizer, attendee } = await deployFixture();
    const price = ethers.parseEther("0.01");

    await contract.connect(organizer).createEvent(1, "Tech Conference", price, 100);
    await expect(
      contract.connect(attendee).buyTicket(1, "eventchain://ticket/1", { value: price })
    ).to.emit(contract, "TicketPurchased");

    expect(await contract.ownerOf(1)).to.equal(attendee.address);
  });

  it("locks and releases vendor escrow", async function () {
    const { contract, organizer, vendor } = await deployFixture();
    const amount = ethers.parseEther("0.2");

    await contract.connect(organizer).createEvent(1, "Concert", 0, 100);
    await contract
      .connect(organizer)
      .createVendorEscrow(1, vendor.address, "Sound system", { value: amount });

    await expect(contract.connect(organizer).releaseVendorEscrow(1))
      .to.emit(contract, "VendorEscrowReleased");
  });
  it("refunds a vendor escrow before release", async function () {
    const { contract, organizer, vendor } = await deployFixture();
    const amount = ethers.parseEther("0.15");

    await contract.connect(organizer).createEvent(1, "Seminar", 0, 100);
    await contract
      .connect(organizer)
      .createVendorEscrow(1, vendor.address, "Catering", { value: amount });

    await expect(contract.connect(organizer).refundVendorEscrow(1))
      .to.emit(contract, "VendorEscrowRefunded");
  });

});
