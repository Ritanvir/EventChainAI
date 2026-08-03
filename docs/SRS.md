# Software Requirements Specification — EventChain AI

## 1. Purpose

EventChain AI is an academic full-stack MVP for planning and operating events with explainable AI assistance and Ethereum-backed trust records.

## 2. Actors

- **Organizer:** creates events, reviews AI plans, publishes events, creates/releases/refunds vendor escrow, withdraws event funds, and checks in tickets.
- **Attendee:** discovers events, purchases an NFT ticket, displays a QR code, and verifies ticket status.
- **Sponsor:** sends transparent sponsorship funds and reviews synchronized contributions.
- **Vendor:** links a wallet and reviews escrow payments assigned to that wallet.
- **Administrator:** reviews system totals, transactions, and application records.

## 3. Functional requirements

| ID | Requirement | Implementation |
|---|---|---|
| FR-01 | Users shall register and log in with a role. | Flask-Login, forms, hashed passwords |
| FR-02 | Organizers shall create and edit an unpublished event. | Event CRUD routes and SQLite |
| FR-03 | The system shall generate an event plan. | LangGraph budget, timeline, risk, resource workflow |
| FR-04 | Organizers shall publish events on Ethereum. | `createEvent` + MetaMask + receipt synchronization |
| FR-05 | Attendees shall purchase unique blockchain tickets. | `buyTicket` mints ERC-721 |
| FR-06 | The system shall prevent duplicate ticket check-in. | `ticketUsed` on-chain flag |
| FR-07 | Sponsors shall send traceable funds. | `sponsorEvent` and transaction mirror |
| FR-08 | Organizers shall lock vendor funds in escrow. | `createVendorEscrow` |
| FR-09 | Organizers shall release or refund escrow once. | settlement-state checks in Solidity |
| FR-10 | Organizers shall withdraw available event funds. | `withdrawEventFunds` |
| FR-11 | Users shall verify a token's owner and usage state. | Web3.py call to `verifyTicket` |
| FR-12 | Administrators shall view system statistics. | role-based dashboard |

## 4. Non-functional requirements

- **Security:** password hashing, CSRF, role checks, MetaMask signing, verified contract receipts, signer matching, and re-entrancy protection.
- **Usability:** responsive web pages and one-click wallet actions with status messages.
- **Auditability:** transaction hashes and decoded event details are retained locally while Ethereum remains the trust source.
- **Maintainability:** application factory, Flask blueprints, service layer, modular templates, and automated tests.
- **Performance:** local SQLite and a local Ethereum node are sufficient for classroom-scale demonstration.
- **Portability:** Windows-focused setup with equivalent Linux/macOS script.

## 5. Constraints

- The supplied implementation targets a local Hardhat network, not real money.
- NFT metadata uses a demonstration URI rather than permanent IPFS/Arweave storage.
- The AI planner is deterministic and does not require a paid LLM API.
- Public deployment requires a smart-contract audit and production infrastructure.

## 6. Acceptance criteria

The MVP is accepted when an organizer can create and publish an event, an attendee can mint a unique ticket, a sponsor can contribute, an organizer can settle vendor escrow, and a ticket can be verified and checked in only once.
