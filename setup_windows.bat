@echo off
setlocal

py -3.11 -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
call npm install
if not exist app\static\vendor mkdir app\static\vendor
copy /Y node_modules\ethers\dist\ethers.min.js app\static\vendor\ethers.min.js
if not exist .env copy .env.example .env
flask --app run.py init-db
flask --app run.py seed-demo

echo.
echo Setup complete.
echo Next: run "npx hardhat node" in Terminal 1.
echo Then deploy in Terminal 2 with "npx hardhat run scripts/deploy.cjs --network localhost".
echo Finally run "python run.py" in Terminal 3.
endlocal
