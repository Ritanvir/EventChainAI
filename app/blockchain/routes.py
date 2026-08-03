from __future__ import annotations

import json
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required
from web3 import Web3

from ..extensions import db
from ..models import (
    BlockchainTransaction,
    Event,
    Sponsorship,
    Ticket,
    User,
    VendorEscrow,
)
from ..services.blockchain_service import BlockchainError, BlockchainService


blockchain_bp = Blueprint("blockchain", __name__, url_prefix="/api/blockchain")


def _json_error(message: str, status: int = 400):
    return jsonify({"ok": False, "message": message}), status


def _normalise_address(address: str) -> str:
    if not Web3.is_address(address):
        raise BlockchainError("Invalid Ethereum wallet address.")
    return Web3.to_checksum_address(address)


def _record_transaction(
    *, tx_hash: str, tx_type: str, event_id: int | None, details: dict
) -> None:
    existing = BlockchainTransaction.query.filter_by(tx_hash=tx_hash).first()
    if existing:
        return
    db.session.add(
        BlockchainTransaction(
            user_id=current_user.id if current_user.is_authenticated else None,
            event_id=event_id,
            tx_type=tx_type,
            tx_hash=tx_hash,
            status="confirmed",
            details_json=json.dumps(details, default=str),
        )
    )


@blockchain_bp.get("/config")
def blockchain_config():
    service = BlockchainService()
    return jsonify(
        {
            "ok": True,
            "configured": service.configured,
            "connected": service.connected,
            "contractAddress": service.deployment.get("address", ""),
            "abi": service.deployment.get("abi", []),
            "chainId": int(
                service.deployment.get(
                    "chainId", current_app.config["BLOCKCHAIN_CHAIN_ID"]
                )
            ),
            "networkName": current_app.config["BLOCKCHAIN_NETWORK_NAME"],
            "rpcUrl": current_app.config["BLOCKCHAIN_RPC_URL"],
        }
    )


@blockchain_bp.post("/wallet")
@login_required
def save_wallet():
    data = request.get_json(silent=True) or {}
    try:
        address = _normalise_address(data.get("walletAddress", ""))
    except BlockchainError as exc:
        return _json_error(str(exc))

    current_user.wallet_address = address
    db.session.commit()
    return jsonify({"ok": True, "walletAddress": address})


@blockchain_bp.post("/sync")
@login_required
def sync_transaction():
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    tx_hash = data.get("txHash", "")

    if action not in {
        "event_created",
        "ticket_purchased",
        "sponsorship_received",
        "escrow_created",
        "escrow_released",
        "escrow_refunded",
        "ticket_checked_in",
        "funds_withdrawn",
    }:
        return _json_error("Unsupported blockchain action.")
    if not tx_hash.startswith("0x") or len(tx_hash) != 66:
        return _json_error("Invalid transaction hash.")

    existing_tx = BlockchainTransaction.query.filter_by(tx_hash=tx_hash).first()
    if existing_tx:
        return jsonify({"ok": True, "message": "Transaction already synchronized."})

    service = BlockchainService()

    try:
        signer = service.get_sender(tx_hash)
        if not current_user.wallet_address:
            raise BlockchainError(
                "Connect the transaction-signing MetaMask wallet before synchronizing."
            )
        if current_user.wallet_address.lower() != signer.lower():
            raise BlockchainError(
                "The transaction was signed by a different MetaMask wallet."
            )

        if action == "event_created":
            args = service.get_single_event(tx_hash, "EventCreated")
            event_id = int(args["eventId"])
            event = db.session.get(Event, event_id)
            if not event:
                raise BlockchainError("The local event does not exist.")
            if event.organizer_id != current_user.id and current_user.role != "admin":
                raise BlockchainError("You are not the organizer of this event.")
            organizer = _normalise_address(args["organizer"])
            expected_price_wei = Web3.to_wei(event.ticket_price_eth, "ether")
            if organizer.lower() != signer.lower():
                raise BlockchainError("The EventCreated organizer does not match the signer.")
            if (
                str(args["title"]) != event.title
                or int(args["ticketPrice"]) != int(expected_price_wei)
                or int(args["maxTickets"]) != event.attendee_capacity
            ):
                raise BlockchainError(
                    "The on-chain event values do not match the local event."
                )
            current_user.wallet_address = organizer
            event.chain_status = "published"
            event.status = "published"
            event.blockchain_tx_hash = tx_hash
            _record_transaction(
                tx_hash=tx_hash,
                tx_type=action,
                event_id=event_id,
                details=args,
            )
            message = "Event publication synchronized."

        elif action == "ticket_purchased":
            args = service.get_single_event(tx_hash, "TicketPurchased")
            event_id = int(args["eventId"])
            token_id = int(args["tokenId"])
            buyer = _normalise_address(args["buyer"])
            event = db.session.get(Event, event_id)
            if not event or event.chain_status != "published":
                raise BlockchainError("The local event is not published on Ethereum.")
            if buyer.lower() != signer.lower():
                raise BlockchainError("The ticket buyer does not match the signer.")
            expected_price_wei = Web3.to_wei(event.ticket_price_eth, "ether")
            if int(args["price"]) != int(expected_price_wei):
                raise BlockchainError("The ticket price does not match the local event.")
            current_user.wallet_address = buyer
            ticket = Ticket.query.filter_by(token_id=token_id).first()
            if not ticket:
                db.session.add(
                    Ticket(
                        event_id=event_id,
                        user_id=current_user.id,
                        buyer_wallet=buyer,
                        token_id=token_id,
                        tx_hash=tx_hash,
                        status="valid",
                    )
                )
            _record_transaction(
                tx_hash=tx_hash,
                tx_type=action,
                event_id=event_id,
                details=args,
            )
            message = f"NFT ticket #{token_id} synchronized."

        elif action == "sponsorship_received":
            args = service.get_single_event(tx_hash, "SponsorshipReceived")
            event_id = int(args["eventId"])
            sponsor = _normalise_address(args["sponsor"])
            amount = service.wei_to_eth(int(args["amount"]))
            event = db.session.get(Event, event_id)
            if not event or event.chain_status != "published":
                raise BlockchainError("The local event is not published on Ethereum.")
            if sponsor.lower() != signer.lower():
                raise BlockchainError("The sponsor does not match the signer.")
            current_user.wallet_address = sponsor
            db.session.add(
                Sponsorship(
                    event_id=event_id,
                    sponsor_user_id=current_user.id,
                    sponsor_wallet=sponsor,
                    amount_eth=amount,
                    tx_hash=tx_hash,
                )
            )
            _record_transaction(
                tx_hash=tx_hash,
                tx_type=action,
                event_id=event_id,
                details=args,
            )
            message = "Sponsorship synchronized."

        elif action == "escrow_created":
            args = service.get_single_event(tx_hash, "VendorEscrowCreated")
            event_id = int(args["eventId"])
            event = db.session.get(Event, event_id)
            if not event or (
                event.organizer_id != current_user.id and current_user.role != "admin"
            ):
                raise BlockchainError("You cannot create an escrow for this event.")
            if event.chain_status != "published":
                raise BlockchainError("The local event is not published on Ethereum.")
            escrow_id = int(args["escrowId"])
            vendor = _normalise_address(args["vendor"])
            amount = service.wei_to_eth(int(args["amount"]))
            vendor_user = User.query.filter(
                db.func.lower(User.wallet_address) == vendor.lower()
            ).first()
            vendor_name = vendor_user.name if vendor_user else "Blockchain vendor"
            db.session.add(
                VendorEscrow(
                    event_id=event_id,
                    chain_escrow_id=escrow_id,
                    vendor_name=vendor_name,
                    vendor_wallet=vendor,
                    description=str(args["description"]),
                    amount_eth=amount,
                    create_tx_hash=tx_hash,
                    status="locked",
                )
            )
            _record_transaction(
                tx_hash=tx_hash,
                tx_type=action,
                event_id=event_id,
                details=args,
            )
            message = f"Vendor escrow #{escrow_id} synchronized."

        elif action == "escrow_released":
            args = service.get_single_event(tx_hash, "VendorEscrowReleased")
            escrow_id = int(args["escrowId"])
            escrow = VendorEscrow.query.filter_by(chain_escrow_id=escrow_id).first()
            if not escrow:
                raise BlockchainError("The local escrow record does not exist.")
            if (
                escrow.event.organizer_id != current_user.id
                and current_user.role != "admin"
            ):
                raise BlockchainError("You cannot release this escrow.")
            escrow.status = "released"
            escrow.release_tx_hash = tx_hash
            escrow.released_at = datetime.now(timezone.utc)
            _record_transaction(
                tx_hash=tx_hash,
                tx_type=action,
                event_id=escrow.event_id,
                details=args,
            )
            message = f"Vendor escrow #{escrow_id} marked released."

        elif action == "escrow_refunded":
            args = service.get_single_event(tx_hash, "VendorEscrowRefunded")
            escrow_id = int(args["escrowId"])
            escrow = VendorEscrow.query.filter_by(chain_escrow_id=escrow_id).first()
            if not escrow:
                raise BlockchainError("The local escrow record does not exist.")
            if (
                escrow.event.organizer_id != current_user.id
                and current_user.role != "admin"
            ):
                raise BlockchainError("You cannot refund this escrow.")
            escrow.status = "refunded"
            escrow.refund_tx_hash = tx_hash
            escrow.refunded_at = datetime.now(timezone.utc)
            _record_transaction(
                tx_hash=tx_hash,
                tx_type=action,
                event_id=escrow.event_id,
                details=args,
            )
            message = f"Vendor escrow #{escrow_id} marked refunded."

        elif action == "ticket_checked_in":
            args = service.get_single_event(tx_hash, "TicketCheckedIn")
            event_id = int(args["eventId"])
            token_id = int(args["tokenId"])
            event = db.session.get(Event, event_id)
            if not event or (
                event.organizer_id != current_user.id and current_user.role != "admin"
            ):
                raise BlockchainError("You cannot check in tickets for this event.")
            ticket = Ticket.query.filter_by(token_id=token_id).first()
            if ticket:
                ticket.status = "used"
                ticket.checked_in_at = datetime.now(timezone.utc)
            _record_transaction(
                tx_hash=tx_hash,
                tx_type=action,
                event_id=event_id,
                details=args,
            )
            message = f"Ticket #{token_id} checked in."

        else:
            args = service.get_single_event(tx_hash, "EventFundsWithdrawn")
            event_id = int(args["eventId"])
            event = db.session.get(Event, event_id)
            if not event or (
                event.organizer_id != current_user.id and current_user.role != "admin"
            ):
                raise BlockchainError("You cannot withdraw from this event.")
            _record_transaction(
                tx_hash=tx_hash,
                tx_type=action,
                event_id=event_id,
                details=args,
            )
            message = "Event fund withdrawal synchronized."

        db.session.commit()
        return jsonify({"ok": True, "message": message})

    except BlockchainError as exc:
        db.session.rollback()
        return _json_error(str(exc))
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Blockchain synchronization failed")
        return _json_error("Unexpected synchronization error.", 500)
