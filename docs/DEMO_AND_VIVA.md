# EventChain AI Demo and Viva Guide

## One-minute introduction

EventChain AI is a full-stack event-management MVP that combines explainable AI planning with Ethereum-based trust. Flask manages users, events, dashboards, and local analytics. LangGraph generates a proposed budget, timeline, risk register, and resource plan. An Ethereum smart contract manages NFT tickets, transparent sponsorship, vendor escrow, organizer withdrawal, and one-time ticket check-in. MetaMask signs transactions, so the application never handles a user's private key.

## Suggested live demonstration

1. Start the Hardhat node, deploy the contract, and run Flask.
2. Log in as organizer and create an event.
3. Explain the AI-generated profile, budget, timeline, risks, and resources.
4. Connect organizer MetaMask and publish the event on Ethereum.
5. Log in as attendee with another Hardhat account and buy an NFT ticket.
6. Show the token ID, transaction hash, and QR ticket.
7. Log in as sponsor and transfer sponsorship ETH.
8. Create vendor escrow and explain that payment is locked until confirmation.
9. Release the escrow and show its on-chain/local status.
10. Check in the NFT ticket and demonstrate that a second check-in is rejected.

## Important viva questions

### Why use both SQLite and Ethereum?

SQLite is fast and suitable for accounts, descriptions, dashboards, and searchable application data. Ethereum is used only for records that benefit from independent verification, such as ticket ownership and financial transactions.

### Why is each ticket an NFT?

An ERC-721 token has a unique token ID and a verifiable owner. The contract also maps the token to an event and tracks whether it has already been checked in.

### How is ticket duplication prevented?

A purchase mints one unique token. Entry verification checks on-chain ownership and the `ticketUsed` flag. After successful check-in, the flag becomes true and the same token cannot be checked in again.

### What is vendor escrow?

The organizer locks ETH in the smart contract for a named vendor. The funds can be released to the vendor after service confirmation or refunded before release, but cannot be settled twice.

### Where is AI used?

A LangGraph workflow analyses the event type, capacity, date, venue, and budget. It returns an explainable budget allocation, timeline, risks, staffing/check-in estimates, and recommendations.

### Is the project production-ready?

No. It is an academic MVP on a local Ethereum development network. A public deployment requires contract auditing, stronger identity/security, production databases, monitoring, legal review, and real payment infrastructure.

## Demo accounts

- Admin: `admin@example.com` / `Admin123!`
- Organizer: `organizer@example.com` / `Organizer123!`
- Attendee: `attendee@example.com` / `Attendee123!`
- Vendor: `vendor@example.com` / `Vendor123!`
- Sponsor: `sponsor@example.com` / `Sponsor123!`
