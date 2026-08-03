# EventChain AI Architecture

## 1. System context

EventChain AI has three cooperating layers:

1. **Browser layer** — Bootstrap-style HTML/CSS, JavaScript, ethers.js, and MetaMask.
2. **Application layer** — Flask routes, authentication, AI planning, dashboards, and transaction synchronisation.
3. **Trust layer** — Ethereum smart contract for NFT tickets, sponsorship funds, ticket check-in, and vendor escrow.

SQLite stores searchable application data, while Ethereum stores the financial and ticket facts that must be independently verifiable.

## 2. Main data flow

```text
User -> Flask form -> SQLite
User -> MetaMask -> Ethereum smart contract
Ethereum receipt -> Flask /blockchain/sync -> SQLite mirror
Organizer event fields -> LangGraph planner -> JSON plan -> SQLite -> dashboard
```

The browser never sends a private key to Flask. MetaMask signs all blockchain transactions locally.

## 3. Flask modules

- `app/auth`: registration, login, logout.
- `app/events`: event CRUD, AI plan, organizer management, tickets, and verification.
- `app/blockchain`: public contract configuration, wallet save, and verified transaction synchronization.
- `app/main`: home and role-based dashboards.
- `app/services/ai_planner.py`: deterministic LangGraph workflow.
- `app/services/blockchain_service.py`: Web3.py receipt and event-log verification.

## 4. Smart-contract responsibilities

`contracts/EventChain.sol` provides:

- `createEvent` — publish an application event on Ethereum.
- `buyTicket` — enforce price/capacity and mint an ERC-721 ticket.
- `sponsorEvent` — record transparent sponsor contributions.
- `createVendorEscrow` — lock organizer funds for a vendor.
- `releaseVendorEscrow` / `refundVendorEscrow` — settle the escrow once.
- `checkInTicket` — mark a token used and stop duplicate entry.
- `withdrawEventFunds` — organizer withdrawal of available ticket/sponsor funds.

## 5. AI workflow

The LangGraph state moves through six nodes:

```text
Analyse event -> Allocate budget -> Build timeline -> Identify risks
-> Recommend resources -> Finalise plan
```

The planner is deterministic and explainable for an academic MVP. No paid AI API is required.

## 6. Database entities

- `User`: account, role, and linked wallet.
- `Event`: planning details and blockchain publication status.
- `Ticket`: local mirror of a minted NFT and check-in state.
- `Sponsorship`: local mirror of sponsor transactions.
- `VendorEscrow`: local mirror of locked/released vendor funds.
- `BlockchainTransaction`: immutable synchronization history in the app.

## 7. Security controls in the MVP

- Password hashing through Werkzeug.
- CSRF protection for Flask forms.
- Role-based route decorators.
- MetaMask signing; no private keys stored by Flask.
- Receipt status, contract address, and decoded event-log verification before local synchronization.
- Solidity access modifiers, checks-effects-interactions, and re-entrancy protection.

## 8. Production work still required

Before public deployment: professional contract audit, HTTPS, PostgreSQL, secret management, RPC provider redundancy, background confirmation monitoring, wallet-signature login, rate limiting, file/object storage, privacy controls, backups, observability, and legal/payment compliance.
