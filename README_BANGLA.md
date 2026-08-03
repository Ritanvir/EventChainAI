# EventChain AI — বাংলা Setup Guide

এই প্রজেক্টটি VS Code-এ চালানোর জন্য নিচের ধাপগুলো ক্রমানুসারে অনুসরণ করুন। এটি local Hardhat Ethereum network ব্যবহার করে; তাই real ETH লাগবে না।

## ১. আগে যা install করবেন

- VS Code
- Python 3.11 অথবা 3.12
- Node.js 22 LTS
- Chrome/Edge browser-এ MetaMask extension
- VS Code extensions: Python, Pylance, Solidity, Prettier

Python install করার সময় **Add Python to PATH** নির্বাচন করুন।

## ২. Project open করুন

ZIP extract করে folder-এর ভেতরে terminal খুলুন:

```powershell
cd path\to\EventChainAI
code .
```

## ৩. Python environment এবং packages

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

PowerShell activation blocked হলে:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\activate
```

## ৪. Ethereum/JavaScript packages

```powershell
npm install
New-Item -ItemType Directory -Force app\static\vendor | Out-Null
Copy-Item node_modules\ethers\dist\ethers.min.js app\static\vendor\ethers.min.js -Force
```

## ৫. Environment file এবং database

```powershell
Copy-Item .env.example .env
flask --app run.py init-db
flask --app run.py seed-demo
```

সব setup এক command-এ করতে চাইলে project root থেকে চালাতে পারেন:

```powershell
setup_windows.bat
```

## ৬. তিনটি VS Code terminal চালু রাখুন

### Terminal 1 — Ethereum node

```powershell
npx hardhat node
```

এই terminal বন্ধ করবেন না। এখানে test account এবং private key দেখাবে।

### Terminal 2 — Smart contract deploy

```powershell
.venv\Scripts\activate
npx hardhat run scripts/deploy.cjs --network localhost
```

সফল হলে `blockchain/deployment.json`-এ contract address ও ABI তৈরি হবে।

### Terminal 3 — Flask server

```powershell
.venv\Scripts\activate
python run.py
```

Browser-এ খুলুন:

```text
http://127.0.0.1:5000
```

## ৭. MetaMask configure করুন

MetaMask → Networks → Add a custom network:

```text
Network name: Hardhat Local
RPC URL: http://127.0.0.1:8545
Chain ID: 31337
Currency symbol: ETH
```

Terminal 1-এ দেখানো Hardhat test account-এর একটি private key import করুন। Demo-তে role বদলানোর সময় আলাদা Hardhat account ব্যবহার করলে flow পরিষ্কার বোঝা যাবে। এই development key কখনো real network-এ ব্যবহার করবেন না।

## ৮. Demo login

```text
Admin: admin@example.com / Admin123!
Organizer: organizer@example.com / Organizer123!
Attendee: attendee@example.com / Attendee123!
Vendor: vendor@example.com / Vendor123!
Sponsor: sponsor@example.com / Sponsor123!
```

## ৯. পূর্ণ demo flow

1. Organizer login করে event create করুন।
2. AI-generated budget, timeline, risk এবং resources দেখুন।
3. Manage page থেকে MetaMask connect করে event Ethereum-এ publish করুন।
4. Attendee login ও অন্য wallet দিয়ে NFT ticket কিনুন।
5. My Tickets page-এ token ID ও QR দেখুন।
6. Sponsor account থেকে ETH sponsorship দিন।
7. Organizer account দিয়ে vendor wallet-এর জন্য escrow create করুন।
8. Service complete হলে release, না হলে refund করুন।
9. Ticket verify করে organizer wallet দিয়ে check-in করুন।
10. একই ticket দ্বিতীয়বার check-in করলে smart contract reject করবে।

## ১০. Tests

```powershell
.venv\Scripts\activate
pytest -q
npm run test:contract
```

## ১১. Hardhat restart করলে

Hardhat node restart হলে আগের local blockchain data মুছে যায়। তাই আবার:

```powershell
npx hardhat run scripts/deploy.cjs --network localhost
flask --app run.py init-db --drop
flask --app run.py seed-demo
```

MetaMask-এ nonce সমস্যা হলে development account-এর activity data clear করুন বা account remove করে একই Hardhat private key আবার import করুন।
