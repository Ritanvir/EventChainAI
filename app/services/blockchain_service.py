from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from flask import current_app
from web3 import Web3


class BlockchainError(RuntimeError):
    pass


class BlockchainService:
    def __init__(self) -> None:
        self.rpc_url = current_app.config["BLOCKCHAIN_RPC_URL"]
        self.deployment_file = Path(
            current_app.config["BLOCKCHAIN_DEPLOYMENT_FILE"]
        )
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 10}))
        self.deployment = self._load_deployment()
        self.contract = None

        address = self.deployment.get("address")
        abi = self.deployment.get("abi") or []
        if address and abi:
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(address), abi=abi
            )

    def _load_deployment(self) -> dict:
        if not self.deployment_file.exists():
            return {}
        try:
            return json.loads(self.deployment_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    @property
    def configured(self) -> bool:
        return bool(self.contract and self.deployment.get("address"))

    @property
    def connected(self) -> bool:
        return self.w3.is_connected()

    def ensure_ready(self) -> None:
        if not self.configured:
            raise BlockchainError(
                "Smart contract is not deployed. Run the Hardhat deployment script."
            )
        if not self.connected:
            raise BlockchainError(
                "Cannot connect to the Ethereum RPC. Start the Hardhat node."
            )

    def get_receipt(self, tx_hash: str):
        self.ensure_ready()
        try:
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
        except Exception as exc:
            raise BlockchainError("Transaction receipt was not found.") from exc

        if receipt.get("status") != 1:
            raise BlockchainError("The blockchain transaction failed.")

        receipt_target = receipt.get("to")
        if not receipt_target or (
            Web3.to_checksum_address(receipt_target) != self.contract.address
        ):
            raise BlockchainError(
                "The transaction was not sent to the deployed EventChain contract."
            )
        return receipt

    def get_sender(self, tx_hash: str) -> str:
        receipt = self.get_receipt(tx_hash)
        sender = receipt.get("from")
        if not sender:
            raise BlockchainError("The transaction signer could not be identified.")
        return Web3.to_checksum_address(sender)

    def get_single_event(self, tx_hash: str, event_name: str) -> dict:
        receipt = self.get_receipt(tx_hash)
        try:
            event_factory = getattr(self.contract.events, event_name)
            logs = event_factory().process_receipt(receipt)
        except Exception as exc:
            raise BlockchainError(
                f"Could not decode the {event_name} event log."
            ) from exc

        if not logs:
            raise BlockchainError(
                f"The transaction does not contain a {event_name} event."
            )
        return dict(logs[0]["args"])

    def verify_ticket(self, token_id: int) -> dict:
        self.ensure_ready()
        try:
            event_id, owner, valid, used = self.contract.functions.verifyTicket(
                token_id
            ).call()
        except Exception as exc:
            raise BlockchainError("Unable to verify this ticket token.") from exc
        return {
            "event_id": int(event_id),
            "owner": owner,
            "valid": bool(valid),
            "used": bool(used),
        }

    @staticmethod
    def wei_to_eth(value: int) -> Decimal:
        return Decimal(value) / Decimal(10**18)
