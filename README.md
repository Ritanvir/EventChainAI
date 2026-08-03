# EventChain AI - Flask + Ethereum Full-Stack Project

EventChain AI is a runnable software-engineering MVP for intelligent and transparent event management. It combines:

- Flask frontend and backend
- SQLite database
- LangGraph-based explainable event-planning workflow
- Ethereum smart contract on a local Hardhat network
- NFT event tickets
- MetaMask payments
- Transparent sponsorship tracking
- Vendor escrow and release
- Blockchain ticket verification and check-in

> This repository is configured for local development and academic demonstration. Never use Hardhat development private keys or this un-audited contract with real funds.

## 1. Main modules

| Module | What it does |
|---|---|
| Authentication | Register/login as organizer, attendee, vendor, sponsor, or admin |
| Event management | Create, edit, publish, and manage events |
| AI planner | Produces a budget, timeline, risks, and resource recommendations |
| NFT ticketing | Mints one ERC-721 ticket for each blockchain purchase |
| Sponsorship | Records sponsor funds on-chain and in the application database |
| Vendor escrow | Organizer locks funds and releases them after service confirmation |
| Verification | Checks NFT ownership and on-chain check-in state |
| Dashboard | Shows role-specific records and transaction status |

## 2. Technology stack

- Python 3.11 or 3.12
- Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF
- LangGraph
- Web3.py
- Solidity 0.8.24
- Hardhat local Ethereum node
- OpenZeppelin ERC-721 contracts
- ethers.js and MetaMask
- SQLite

## 3. Install these first

1. **VS Code**
2. **Python 3.11 or 3.12** - tick `Add Python to PATH` during installation
3. **Node.js 22 LTS**
4. **MetaMask browser extension**
5. Optional: Git

Recommended VS Code extensions:

- Python by Microsoft
- Pylance
- Solidity by Juan Blanco
- Prettier

## 4. Open the project in VS Code

```powershell
cd path\to\EventChainAI
code .
```

Open a VS Code terminal with **Terminal > New Terminal**.

## 5. One-time setup on Windows

### 5.1 Create and activate a Python virtual environment

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run this once in the same terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\activate
```

### 5.2 Install blockchain packages

```powershell
npm install
```

Copy the browser build of ethers.js into Flask static files:

```powershell
New-Item -ItemType Directory -Force app\static\vendor | Out-Null
Copy-Item node_modules\ethers\dist\ethers.min.js app\static\vendor\ethers.min.js -Force
```

### 5.3 Create environment file

```powershell
Copy-Item .env.example .env
```

For a local demo, the default values are sufficient.

### 5.4 Initialise the database

```powershell
flask --app run.py init-db
flask --app run.py seed-demo
```

Demo logins:

| Role | Email | Password |
|---|---|---|
| Admin | admin@example.com | Admin123! |
| Organizer | organizer@example.com | Organizer123! |
| Attendee | attendee@example.com | Attendee123! |
| Vendor | vendor@example.com | Vendor123! |
| Sponsor | sponsor@example.com | Sponsor123! |

## 6. Start the Ethereum network and deploy the contract

You need three terminals.

### Terminal 1 - local Ethereum node

```powershell
npx hardhat node
```

Keep this terminal running. Hardhat prints funded test accounts and private keys.

### Terminal 2 - deploy the smart contract

```powershell
.venv\Scripts\activate
npx hardhat run scripts/deploy.cjs --network localhost
```

The deployment script writes the contract address and ABI to:

```text
blockchain/deployment.json
```

### Add Hardhat to MetaMask

Use **Add network manually**:

- Network name: `Hardhat Local`
- RPC URL: `http://127.0.0.1:8545`
- Chain ID: `31337`
- Currency symbol: `ETH`

Then import one of the private keys printed by `npx hardhat node`.

**Important:** those keys are public development keys. Never use them on a real network.

## 7. Start Flask

### Terminal 3

```powershell
.venv\Scripts\activate
python run.py
```

Open:

```text
http://127.0.0.1:5000
```

## 8. Recommended demonstration sequence

1. Log in as the organizer.
2. Create an event and review the generated AI plan.
3. Open **Manage event** and connect MetaMask.
4. Click **Publish on Ethereum**.
5. Log in as an attendee, connect a different Hardhat account, and buy a ticket.
6. Open **My tickets** and inspect the token ID and QR code.
7. Log in as a sponsor and send sponsorship funds.
8. Log back in as organizer and create a vendor escrow.
9. Release the escrow after service confirmation.
10. Verify and check in the ticket from the verification page.

## 9. AI planner design

The MVP uses a deterministic LangGraph workflow, so it runs without a paid API key. Its nodes:

1. Analyse event category, capacity, date, and venue.
2. Allocate budget using category-specific weights.
3. Build a preparation timeline.
4. Identify operational and financial risks.
5. Produce final recommendations.

This makes the output explainable and reproducible. A future version can replace or extend individual nodes with an LLM.

## 10. Blockchain flow

### Publish event

The organizer signs `createEvent()` in MetaMask. Flask verifies the transaction receipt and stores the transaction hash.

### Buy ticket

The attendee signs `buyTicket()` and sends the exact ticket price. The contract mints an ERC-721 token and emits `TicketPurchased`. Flask verifies the log and stores the token ID.

### Sponsorship

The sponsor calls `sponsorEvent()`. The contract adds the amount to the event's transparent balance.

### Vendor escrow

The organizer calls `createVendorEscrow()` with ETH. Later, `releaseVendorEscrow()` transfers the locked amount to the vendor.

### Ticket check-in

The organizer calls `checkInTicket()`. The token is marked used on-chain and cannot be checked in twice.

## 11. Run tests

```powershell
.venv\Scripts\activate
pytest -q
npm run test:contract
```

## 12. Useful commands

Reset the local database:

```powershell
flask --app run.py init-db --drop
flask --app run.py seed-demo
```

Recompile contracts:

```powershell
npx hardhat compile
```

Redeploy after restarting Hardhat:

```powershell
npx hardhat run scripts/deploy.cjs --network localhost
```

## 13. Common problems

### `ethers is not defined`

Run:

```powershell
Copy-Item node_modules\ethers\dist\ethers.min.js app\static\vendor\ethers.min.js -Force
```

Then hard-refresh the browser with `Ctrl+F5`.

### Flask says blockchain is not configured

Deploy the contract again and confirm that `blockchain/deployment.json` contains a non-empty address.

### MetaMask wrong network

Switch to Chain ID `31337`, or click the application's **Connect wallet** button and approve adding the local network.

### Transaction fails after restarting Hardhat

Restarting Hardhat erases the local blockchain. Deploy the contract again. Old transaction hashes and token IDs will no longer exist on the new chain. For a clean demo, also reset the SQLite database.

### `nonce too high` in MetaMask

Open MetaMask settings and clear activity/tab data for the development account, or remove and re-import the Hardhat test account.

## 14. Validation notes

The repository includes Python route/planner tests and Solidity contract tests. Run both after dependency installation. The contract is intended for a local academic demonstration and has not received a professional security audit.

## 15. Production improvements

Before real deployment, add:

- Professional smart-contract audit
- PostgreSQL and database migrations
- HTTPS and secure cookie configuration
- IPFS/Arweave metadata for NFT tickets
- Email verification and password recovery
- Role approval and stronger identity verification
- Oracle-based fiat conversion
- Event cancellation/refund rules
- Rate limiting, logging, monitoring, and backups
- Testnet deployment before any mainnet use
