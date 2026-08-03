# EventChain AI Test Cases

| ID | Scenario | Expected result |
|---|---|---|
| TC-01 | Register a new organizer with valid fields | Account created and dashboard opens |
| TC-02 | Register with an existing email | Validation error shown |
| TC-03 | Attendee opens event-create route | HTTP 403 access denied |
| TC-04 | Organizer creates event | Event saved and AI plan generated |
| TC-05 | Enter a past event date | Form rejects the date |
| TC-06 | Publish local event through MetaMask | `EventCreated` confirmed and local status becomes published |
| TC-07 | Synchronize transaction from a different wallet | Flask rejects signer mismatch |
| TC-08 | Buy ticket with exact price | ERC-721 token minted and local ticket synchronized |
| TC-09 | Buy ticket with incorrect price | Smart contract reverts |
| TC-10 | Buy after capacity is reached | Smart contract reports sold out |
| TC-11 | Sponsor event with zero ETH | Smart contract reverts |
| TC-12 | Sponsor active event with positive ETH | Sponsorship total and available balance increase |
| TC-13 | Create vendor escrow | ETH locks and escrow record is created |
| TC-14 | Release vendor escrow | Vendor receives funds and escrow closes |
| TC-15 | Refund vendor escrow | Organizer receives funds and escrow closes |
| TC-16 | Settle the same escrow twice | Smart contract reverts |
| TC-17 | Verify unused token | Valid owner and unused status returned |
| TC-18 | Organizer checks in token | `ticketUsed` becomes true |
| TC-19 | Check in same token twice | Smart contract reverts |
| TC-20 | Restart Hardhat and use an old transaction | Receipt cannot be found; redeployment/reset required |

Automated coverage is provided in `tests/` for Flask and AI behavior and in `test/EventChain.test.cjs` for core Solidity flows.
