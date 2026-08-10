(() => {
  const AUTO_DISMISS_MS = 6000;
  const MAX_VISIBLE = 4;
  const ICONS = { success: "✓", danger: "!", warning: "!", info: "i" };

  const stack = () => document.getElementById("toast-stack");

  function dismiss(toast) {
    if (toast.dataset.leaving) return;
    toast.dataset.leaving = "true";
    toast.classList.add("is-leaving");
    const remove = () => toast.remove();
    toast.addEventListener("transitionend", remove, { once: true });
    // transitionend never fires when motion is reduced, so remove regardless.
    setTimeout(remove, 400);
  }

  function scheduleDismiss(toast) {
    // Errors stay until dismissed: they carry MetaMask and server text worth reading.
    if (toast.dataset.type === "danger") return;
    let timer = null;
    const start = () => { timer = setTimeout(() => dismiss(toast), AUTO_DISMISS_MS); };
    const pause = () => { clearTimeout(timer); };
    toast.addEventListener("mouseenter", pause);
    toast.addEventListener("focusin", pause);
    toast.addEventListener("mouseleave", start);
    toast.addEventListener("focusout", start);
    start();
  }

  function activate(toast) {
    if (toast.dataset.ready) return;
    toast.dataset.ready = "true";
    // Cancels the CSS-only fade so the timers below own the lifetime from here.
    toast.classList.add("is-managed");
    const close = toast.querySelector(".toast-close");
    if (close) close.addEventListener("click", () => dismiss(toast));
    scheduleDismiss(toast);
  }

  function trim() {
    const host = stack();
    if (!host) return;
    const live = [...host.querySelectorAll(".toast:not([data-leaving])")];
    // Only auto-dismissing toasts are trimmed, so the cap can never discard an
    // unread error.
    const disposable = live.filter((t) => t.dataset.type !== "danger");
    const excess = live.length - MAX_VISIBLE;
    if (excess > 0) disposable.slice(0, excess).forEach(dismiss);
  }

  function showToast(message, type = "info") {
    const host = stack();
    if (!host) return null;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.dataset.type = type;

    const icon = document.createElement("span");
    icon.className = "toast-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = ICONS[type] || ICONS.info;

    const body = document.createElement("p");
    body.className = "toast-message";
    body.textContent = message;

    const close = document.createElement("button");
    close.className = "toast-close";
    close.type = "button";
    close.setAttribute("aria-label", "Dismiss notification");
    close.textContent = "×";

    toast.append(icon, body, close);
    host.appendChild(toast);
    activate(toast);
    trim();
    return toast;
  }

  window.showToast = showToast;

  // Server-rendered flashes ship inside the stack already; adopt them on load.
  document.addEventListener("DOMContentLoaded", () => {
    const host = stack();
    if (host) host.querySelectorAll(".toast").forEach(activate);
  });
})();
