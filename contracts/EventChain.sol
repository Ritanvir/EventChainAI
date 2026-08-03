// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

contract EventChain is ERC721URIStorage, Ownable, ReentrancyGuard {
    struct EventInfo {
        address organizer;
        string title;
        uint256 ticketPrice;
        uint256 maxTickets;
        uint256 sold;
        uint256 availableBalance;
        uint256 sponsorshipTotal;
        bool active;
    }

    struct VendorEscrow {
        uint256 eventId;
        address organizer;
        address vendor;
        uint256 amount;
        string description;
        bool released;
        bool refunded;
    }

    mapping(uint256 => EventInfo) public eventsData;
    mapping(uint256 => uint256) public ticketEvent;
    mapping(uint256 => bool) public ticketUsed;
    mapping(uint256 => VendorEscrow) public vendorEscrows;

    uint256 private _nextTokenId = 1;
    uint256 private _nextEscrowId = 1;

    event EventCreated(
        uint256 indexed eventId,
        address indexed organizer,
        string title,
        uint256 ticketPrice,
        uint256 maxTickets
    );
    event EventStatusChanged(uint256 indexed eventId, bool active);
    event TicketPurchased(
        uint256 indexed eventId,
        uint256 indexed tokenId,
        address indexed buyer,
        uint256 price
    );
    event TicketCheckedIn(
        uint256 indexed eventId,
        uint256 indexed tokenId,
        address indexed checkedInBy
    );
    event SponsorshipReceived(
        uint256 indexed eventId,
        address indexed sponsor,
        uint256 amount
    );
    event EventFundsWithdrawn(
        uint256 indexed eventId,
        address indexed organizer,
        uint256 amount
    );
    event VendorEscrowCreated(
        uint256 indexed escrowId,
        uint256 indexed eventId,
        address indexed vendor,
        uint256 amount,
        string description
    );
    event VendorEscrowReleased(
        uint256 indexed escrowId,
        address indexed vendor,
        uint256 amount
    );
    event VendorEscrowRefunded(
        uint256 indexed escrowId,
        address indexed organizer,
        uint256 amount
    );

    constructor() ERC721("EventChain Ticket", "ECT") Ownable(msg.sender) {}

    modifier onlyEventOrganizer(uint256 eventId) {
        require(
            eventsData[eventId].organizer == msg.sender,
            "Only the event organizer can perform this action"
        );
        _;
    }

    function createEvent(
        uint256 eventId,
        string calldata title,
        uint256 ticketPrice,
        uint256 maxTickets
    ) external {
        require(eventId > 0, "Invalid event ID");
        require(bytes(title).length > 0, "Title is required");
        require(maxTickets > 0, "Capacity must be greater than zero");
        require(
            eventsData[eventId].organizer == address(0),
            "Event already exists"
        );

        eventsData[eventId] = EventInfo({
            organizer: msg.sender,
            title: title,
            ticketPrice: ticketPrice,
            maxTickets: maxTickets,
            sold: 0,
            availableBalance: 0,
            sponsorshipTotal: 0,
            active: true
        });

        emit EventCreated(
            eventId,
            msg.sender,
            title,
            ticketPrice,
            maxTickets
        );
    }

    function setEventActive(
        uint256 eventId,
        bool active
    ) external onlyEventOrganizer(eventId) {
        eventsData[eventId].active = active;
        emit EventStatusChanged(eventId, active);
    }

    function buyTicket(
        uint256 eventId,
        string calldata metadataURI
    ) external payable nonReentrant returns (uint256 tokenId) {
        EventInfo storage eventInfo = eventsData[eventId];
        require(eventInfo.organizer != address(0), "Event does not exist");
        require(eventInfo.active, "Event is not active");
        require(eventInfo.sold < eventInfo.maxTickets, "Event is sold out");
        require(msg.value == eventInfo.ticketPrice, "Incorrect ticket price");

        tokenId = _nextTokenId++;
        eventInfo.sold += 1;
        eventInfo.availableBalance += msg.value;
        ticketEvent[tokenId] = eventId;

        _safeMint(msg.sender, tokenId);
        _setTokenURI(tokenId, metadataURI);

        emit TicketPurchased(eventId, tokenId, msg.sender, msg.value);
    }

    function checkInTicket(uint256 tokenId) external {
        address ticketOwner = _ownerOf(tokenId);
        require(ticketOwner != address(0), "Ticket does not exist");

        uint256 eventId = ticketEvent[tokenId];
        require(
            eventsData[eventId].organizer == msg.sender,
            "Only the event organizer can check in"
        );
        require(!ticketUsed[tokenId], "Ticket already checked in");

        ticketUsed[tokenId] = true;
        emit TicketCheckedIn(eventId, tokenId, msg.sender);
    }

    function sponsorEvent(uint256 eventId) external payable {
        EventInfo storage eventInfo = eventsData[eventId];
        require(eventInfo.organizer != address(0), "Event does not exist");
        require(eventInfo.active, "Event is not active");
        require(msg.value > 0, "Sponsorship must be greater than zero");

        eventInfo.sponsorshipTotal += msg.value;
        eventInfo.availableBalance += msg.value;

        emit SponsorshipReceived(eventId, msg.sender, msg.value);
    }

    function withdrawEventFunds(
        uint256 eventId,
        uint256 amount
    ) external nonReentrant onlyEventOrganizer(eventId) {
        EventInfo storage eventInfo = eventsData[eventId];
        require(amount > 0, "Amount must be greater than zero");
        require(
            amount <= eventInfo.availableBalance,
            "Insufficient event balance"
        );

        eventInfo.availableBalance -= amount;
        (bool success, ) = payable(msg.sender).call{value: amount}("");
        require(success, "Transfer failed");

        emit EventFundsWithdrawn(eventId, msg.sender, amount);
    }

    function createVendorEscrow(
        uint256 eventId,
        address vendor,
        string calldata description
    ) external payable onlyEventOrganizer(eventId) returns (uint256 escrowId) {
        require(vendor != address(0), "Invalid vendor address");
        require(msg.value > 0, "Escrow amount must be greater than zero");

        escrowId = _nextEscrowId++;
        vendorEscrows[escrowId] = VendorEscrow({
            eventId: eventId,
            organizer: msg.sender,
            vendor: vendor,
            amount: msg.value,
            description: description,
            released: false,
            refunded: false
        });

        emit VendorEscrowCreated(
            escrowId,
            eventId,
            vendor,
            msg.value,
            description
        );
    }

    function releaseVendorEscrow(
        uint256 escrowId
    ) external nonReentrant {
        VendorEscrow storage escrow = vendorEscrows[escrowId];
        require(escrow.organizer != address(0), "Escrow does not exist");
        require(escrow.organizer == msg.sender, "Only organizer can release");
        require(!escrow.released && !escrow.refunded, "Escrow already closed");

        escrow.released = true;
        (bool success, ) = payable(escrow.vendor).call{value: escrow.amount}("");
        require(success, "Vendor payment failed");

        emit VendorEscrowReleased(escrowId, escrow.vendor, escrow.amount);
    }

    function refundVendorEscrow(
        uint256 escrowId
    ) external nonReentrant {
        VendorEscrow storage escrow = vendorEscrows[escrowId];
        require(escrow.organizer != address(0), "Escrow does not exist");
        require(escrow.organizer == msg.sender, "Only organizer can refund");
        require(!escrow.released && !escrow.refunded, "Escrow already closed");

        escrow.refunded = true;
        (bool success, ) = payable(escrow.organizer).call{value: escrow.amount}("");
        require(success, "Refund failed");

        emit VendorEscrowRefunded(escrowId, escrow.organizer, escrow.amount);
    }

    function verifyTicket(
        uint256 tokenId
    ) external view returns (
        uint256 eventId,
        address owner,
        bool valid,
        bool used
    ) {
        owner = _ownerOf(tokenId);
        eventId = ticketEvent[tokenId];
        valid = owner != address(0);
        used = ticketUsed[tokenId];
    }
}
