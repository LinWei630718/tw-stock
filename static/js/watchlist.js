/**
 * Watchlist & Popular Categories Manager
 */

class WatchlistManager {
  constructor(watchlistContainerId, categoriesContainerId, onSelectStock) {
    this.watchlistContainer = document.getElementById(watchlistContainerId);
    this.categoriesContainer = document.getElementById(categoriesContainerId);
    this.onSelectStock = onSelectStock;

    this.storageKey = "tw_stock_watchlist_v1";
    this.watchlist = this.loadWatchlist();
    this.currentCode = "2330";

    this.init();
  }

  loadWatchlist() {
    try {
      const saved = localStorage.getItem(this.storageKey);
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {}
    // Default initial watchlist
    return [
      { code: "2330", name: "台積電", symbol: "2330.TW" },
      { code: "2317", name: "鴻海", symbol: "2317.TW" },
      { code: "2454", name: "聯發科", symbol: "2454.TW" },
      { code: "2382", name: "廣達", symbol: "2382.TW" },
      { code: "0050", name: "元大台灣50", symbol: "0050.TW" },
      { code: "2603", name: "長榮", symbol: "2603.TW" },
      { code: "8069", name: "元太", symbol: "8069.TWO" }
    ];
  }

  saveWatchlist() {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(this.watchlist));
    } catch (e) {}
  }

  isPinned(code) {
    return this.watchlist.some(item => item.code === code);
  }

  togglePin(stockInfo) {
    const code = stockInfo.code;
    if (this.isPinned(code)) {
      this.watchlist = this.watchlist.filter(item => item.code !== code);
    } else {
      this.watchlist.unshift({
        code: code,
        name: stockInfo.name,
        symbol: stockInfo.symbol
      });
    }
    this.saveWatchlist();
    this.renderWatchlist();
    this.updatePinButton(code);
  }

  updatePinButton(code) {
    const btn = document.getElementById("watchlist-pin-btn");
    if (!btn) return;
    const pinned = this.isPinned(code);
    btn.classList.toggle("pinned", pinned);
    btn.title = pinned ? "從自選股移除" : "加入自選股";
    btn.innerHTML = pinned ? "★" : "☆";
  }

  async init() {
    this.renderWatchlist();
    await this.loadCategories();
  }

  renderWatchlist() {
    if (!this.watchlistContainer) return;

    if (this.watchlist.length === 0) {
      this.watchlistContainer.innerHTML = `
        <div style="padding:20px; text-align:center; color:var(--text-muted); font-size:12px;">
          尚未加入自選股<br>點選頂部 ★ 即可收藏關注個股
        </div>
      `;
      return;
    }

    let html = "";
    this.watchlist.forEach(item => {
      const isSelected = item.code === this.currentCode;
      html += `
        <div class="stock-list-item ${isSelected ? 'selected' : ''}" data-code="${item.code}">
          <div class="item-info">
            <span class="item-name">${item.name}</span>
            <span class="item-code">${item.code}</span>
          </div>
          <div class="item-price-block">
            <span style="font-size:11px; color:var(--color-accent); font-weight:600;">查看分析 ›</span>
          </div>
        </div>
      `;
    });

    this.watchlistContainer.innerHTML = html;

    // Click events
    this.watchlistContainer.querySelectorAll(".stock-list-item").forEach(el => {
      el.addEventListener("click", () => {
        const code = el.dataset.code;
        if (code && this.onSelectStock) {
          this.currentCode = code;
          this.highlightSelected();
          this.onSelectStock(code);
        }
      });
    });
  }

  async loadCategories() {
    if (!this.categoriesContainer) return;
    try {
      const res = await API.getCategories();
      const categories = res.categories || {};

      let html = "";
      Object.keys(categories).forEach(catName => {
        const list = categories[catName];
        html += `<div class="category-header">${catName} (${list.length})</div>`;
        list.forEach(item => {
          const isSelected = item.code === this.currentCode;
          html += `
            <div class="stock-list-item ${isSelected ? 'selected' : ''}" data-code="${item.code}">
              <div class="item-info">
                <span class="item-name">${item.name}</span>
                <span class="item-code">${item.code} · ${item.industry}</span>
              </div>
              <div class="item-price-block">
                <span style="font-size:10px; color:var(--text-muted);">${item.market}</span>
              </div>
            </div>
          `;
        });
      });

      this.categoriesContainer.innerHTML = html;

      // Click events
      this.categoriesContainer.querySelectorAll(".stock-list-item").forEach(el => {
        el.addEventListener("click", () => {
          const code = el.dataset.code;
          if (code && this.onSelectStock) {
            this.currentCode = code;
            this.highlightSelected();
            this.onSelectStock(code);
          }
        });
      });
    } catch (err) {
      console.error("Failed to load categories:", err);
    }
  }

  setCurrentStock(code) {
    this.currentCode = code;
    this.highlightSelected();
    this.updatePinButton(code);
  }

  highlightSelected() {
    document.querySelectorAll(".stock-list-item").forEach(el => {
      el.classList.toggle("selected", el.dataset.code === this.currentCode);
    });
  }
}
