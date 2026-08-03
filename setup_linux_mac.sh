#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
npm install
mkdir -p app/static/vendor
cp node_modules/ethers/dist/ethers.min.js app/static/vendor/ethers.min.js
[ -f .env ] || cp .env.example .env
flask --app run.py init-db
flask --app run.py seed-demo

echo "Setup complete. Start Hardhat, deploy, then run Flask."
