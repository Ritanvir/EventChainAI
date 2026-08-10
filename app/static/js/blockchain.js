(() => {
  let config = null;
  let provider = null;
  let signer = null;
  let contract = null;
  let account = null;

  const csrfToken = () =>
    document.querySelector('meta[name="csrf-token"]')?.content || "";

  function alertUser(message, type = "info") {
    if (typeof window.showToast === "function") {
      window.showToast(message, type);
    } else {
      console.warn(`[EventChain] ${type}: ${message}`);
    }
  }

  function setLoading(active, message = "Processing transaction…") {
    const overlay = document.getElementById("loading-overlay");
    const label = document.getElementById("loading-message");
    if (!overlay) return;
    if (label) label.textContent = message;
    overlay.hidden = !active;
  }

  async function postJSON(url, body) {
    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken()
      },
      body: JSON.stringify(body)
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.message || "The request failed.");
    }
    return data;
  }

  async function loadConfig() {
    if (config) return config;
    const response = await fetch("/api/blockchain/config");
    config = await response.json();
    if (!config.configured) {
      throw new Error(
        "Smart contract is not deployed. Follow README deployment steps."
      );
    }
    return config;
  }

  async function ensureNetwork() {
    const cfg = await loadConfig();
    const expectedHex = `0x${Number(cfg.chainId).toString(16)}`;
    const currentHex = await window.ethereum.request({ method: "eth_chainId" });
    if (currentHex.toLowerCase() === expectedHex.toLowerCase()) return;

    try {
      await window.ethereum.request({
        method: "wallet_switchEthereumChain",
        params: [{ chainId: expectedHex }]
      });
    } catch (error) {
      if (error.code !== 4902) throw error;
      await window.ethereum.request({
        method: "wallet_addEthereumChain",
        params: [{
          chainId: expectedHex,
          chainName: cfg.networkName,
          rpcUrls: [cfg.rpcUrl],
          nativeCurrency: { name: "Ether", symbol: "ETH", decimals: 18 }
        }]
      });
    }
  }

  function updateWalletButton() {
    const button = document.getElementById("connect-wallet");
    if (!button) return;
    button.textContent = account
      ? `${account.slice(0, 6)}…${account.slice(-4)}`
      : "Connect wallet";
  }

  async function connectWallet() {
    if (!window.ethereum) {
      throw new Error("MetaMask is not installed in this browser.");
    }
    if (!window.ethers) {
      throw new Error(
        "ethers.js is missing. Copy it from node_modules as shown in README."
      );
    }

    await ensureNetwork();
    const accounts = await window.ethereum.request({
      method: "eth_requestAccounts"
    });
    account = accounts[0];
    provider = new ethers.BrowserProvider(window.ethereum);
    signer = await provider.getSigner();
    const cfg = await loadConfig();
    contract = new ethers.Contract(cfg.contractAddress, cfg.abi, signer);
    updateWalletButton();

    try {
      await postJSON("/api/blockchain/wallet", { walletAddress: account });
    } catch (error) {
      console.warn(error.message);
    }
    return account;
  }

  async function ready() {
    if (!contract || !signer) await connectWallet();
    return contract;
  }

  async function sync(action, txHash) {
    return postJSON("/api/blockchain/sync", { action, txHash });
  }

  async function execute(message, transactionFactory, action) {
    try {
      setLoading(true, message);
      await ready();
      const tx = await transactionFactory();
      setLoading(true, "Waiting for Ethereum confirmation…");
      await tx.wait();
      const result = await sync(action, tx.hash);
      alertUser(result.message, "success");
      setTimeout(() => window.location.reload(), 900);
    } catch (error) {
      console.error(error);
      const messageText =
        error.shortMessage ||
        error.reason ||
        error.message ||
        "Transaction failed.";
      alertUser(messageText, "danger");
    } finally {
      setLoading(false);
    }
  }

  async function publishEvent(eventId, title, priceEth, capacity) {
    await execute(
      "Publishing event on Ethereum…",
      async () => {
        const c = await ready();
        return c.createEvent(
          eventId,
          title,
          ethers.parseEther(String(priceEth)),
          capacity
        );
      },
      "event_created"
    );
  }

  async function buyTicket(eventId, priceEth) {
    await execute(
      "Buying and minting your NFT ticket…",
      async () => {
        const c = await ready();
        const metadataURI =
          `eventchain://ticket/${eventId}/${account}/${Date.now()}`;
        return c.buyTicket(eventId, metadataURI, {
          value: ethers.parseEther(String(priceEth))
        });
      },
      "ticket_purchased"
    );
  }

  async function sponsorEvent(eventId) {
    const input = document.getElementById(`sponsor-amount-${eventId}`);
    const amount = input?.value;
    if (!amount || Number(amount) <= 0) {
      alertUser("Enter a sponsorship amount greater than zero.", "warning");
      return;
    }
    await execute(
      "Sending transparent sponsorship…",
      async () => {
        const c = await ready();
        return c.sponsorEvent(eventId, {
          value: ethers.parseEther(String(amount))
        });
      },
      "sponsorship_received"
    );
  }

  async function createEscrow(eventId) {
    const vendor = document.getElementById("vendor-wallet")?.value.trim();
    const description =
      document.getElementById("vendor-description")?.value.trim();
    const amount = document.getElementById("vendor-amount")?.value;

    if (!vendor || !ethers.isAddress(vendor)) {
      alertUser("Enter a valid vendor Ethereum address.", "warning");
      return;
    }
    if (!description) {
      alertUser("Enter the vendor service description.", "warning");
      return;
    }
    if (!amount || Number(amount) <= 0) {
      alertUser("Enter an escrow amount greater than zero.", "warning");
      return;
    }

    await execute(
      "Locking vendor funds in smart-contract escrow…",
      async () => {
        const c = await ready();
        return c.createVendorEscrow(eventId, vendor, description, {
          value: ethers.parseEther(String(amount))
        });
      },
      "escrow_created"
    );
  }

  async function releaseEscrow(escrowId) {
    if (!window.confirm(`Release escrow #${escrowId} to the vendor?`)) return;
    await execute(
      "Releasing vendor escrow…",
      async () => (await ready()).releaseVendorEscrow(escrowId),
      "escrow_released"
    );
  }

  async function refundEscrow(escrowId) {
    if (!window.confirm(`Refund escrow #${escrowId} to the organizer?`)) return;
    await execute(
      "Refunding vendor escrow…",
      async () => (await ready()).refundVendorEscrow(escrowId),
      "escrow_refunded"
    );
  }

  async function checkInTicket(tokenId) {
    if (
      !window.confirm(
        `Check in NFT ticket #${tokenId}? This cannot be repeated.`
      )
    ) return;
    await execute(
      "Recording ticket check-in on Ethereum…",
      async () => (await ready()).checkInTicket(tokenId),
      "ticket_checked_in"
    );
  }

  async function withdrawFunds(eventId) {
    const amount = document.getElementById("withdraw-amount")?.value;
    if (!amount || Number(amount) <= 0) {
      alertUser("Enter a withdrawal amount greater than zero.", "warning");
      return;
    }
    await execute(
      "Withdrawing event funds…",
      async () =>
        (await ready()).withdrawEventFunds(
          eventId,
          ethers.parseEther(String(amount))
        ),
      "funds_withdrawn"
    );
  }

  document.addEventListener("DOMContentLoaded", () => {
    const button = document.getElementById("connect-wallet");
    if (button) {
      button.addEventListener("click", async () => {
        try {
          setLoading(true, "Connecting MetaMask…");
          await connectWallet();
          alertUser("MetaMask wallet connected.", "success");
        } catch (error) {
          alertUser(error.message, "danger");
        } finally {
          setLoading(false);
        }
      });
    }

    if (window.ethereum) {
      window.ethereum.on("accountsChanged", () => window.location.reload());
      window.ethereum.on("chainChanged", () => window.location.reload());
      window.ethereum.request({ method: "eth_accounts" }).then((accounts) => {
        if (accounts.length) {
          account = accounts[0];
          updateWalletButton();
        }
      });
    }
  });

  window.EventChain = {
    connectWallet,
    publishEvent,
    buyTicket,
    sponsorEvent,
    createEscrow,
    releaseEscrow,
    refundEscrow,
    checkInTicket,
    withdrawFunds
  };
})();
