/**
 * Glassmorphic Toast Notification System for Taiwan Stock Pro
 * Zero external dependencies, supports error, success, warning, and info
 */

class ToastManager {
  constructor() {
    this.container = null;
    this.init();
  }

  init() {
    if (document.getElementById("toast-container")) {
      this.container = document.getElementById("toast-container");
      return;
    }
    this.container = document.createElement("div");
    this.container.id = "toast-container";
    this.container.className = "toast-container";
    document.body.appendChild(this.container);
  }

  show(message, type = "info", duration = 3500) {
    if (!this.container) this.init();

    const icons = {
      error: "❌",
      success: "✅",
      warning: "⚠️",
      info: "ℹ️"
    };

    const toast = document.createElement("div");
    toast.className = `toast-item toast-${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${icons[type] || icons.info}</span>
      <span class="toast-message">${message}</span>
      <button class="toast-close" aria-label="Close">&times;</button>
    `;

    const closeBtn = toast.querySelector(".toast-close");
    const removeToast = () => {
      toast.classList.add("toast-hiding");
      setTimeout(() => {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast);
        }
      }, 250);
    };

    closeBtn.addEventListener("click", removeToast);
    toast.addEventListener("click", (e) => {
      if (e.target !== closeBtn) removeToast();
    });

    this.container.appendChild(toast);

    // Auto remove after duration
    if (duration > 0) {
      setTimeout(() => {
        if (toast.parentNode) removeToast();
      }, duration);
    }

    return toast;
  }

  error(msg, duration = 4000) {
    return this.show(msg, "error", duration);
  }

  success(msg, duration = 3000) {
    return this.show(msg, "success", duration);
  }

  warning(msg, duration = 3500) {
    return this.show(msg, "warning", duration);
  }

  info(msg, duration = 3000) {
    return this.show(msg, "info", duration);
  }
}

// Global Singleton Instance
window.Toast = new ToastManager();
