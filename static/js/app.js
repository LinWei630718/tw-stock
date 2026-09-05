/**
 * Main Application Controller for Taiwan Stock Technical Analysis System
 */

document.addEventListener("DOMContentLoaded", () => {
  // Global State
  const state = {
    currentCode: "2330",
    currentStockSummary: null,
    interval: "1d",
    range: "1y",
    isTaiwanColor: true,
    isLoading: false
  };

  // UI Components
  const chartManager = new ChartManager(
    "main-chart-container",
    "sub-chart-container",
    "chart-legend-box"
  );

  const diagnosticUI = new DiagnosticUI("diagnostic-body");

  const watchlistManager = new WatchlistManager(
    "watchlist-items-box",
    "categories-items-box",
    (code) => loadStock(code)
  );

  const screenerUI = new ScreenerUI("screener-body", (code) => {
    switchView("chart");
    loadStock(code);
  });
  const backtestUI = new BacktestUI("backtest-body", (markers) => {
    chartManager.setTradeMarkers(markers);
  });

  // Dashboard UI
  const dashboardUI = new DashboardUI("dashboard-view-container", (code) => {
    switchView("chart");
    loadStock(code);
  });

  // ETF Dashboard UI
  const etfDashboardUI = new EtfDashboardUI("etf-dashboard-view-container", (code) => {
    switchView("chart");
    loadStock(code);
  });

  // CSV Loader
  const csvLoader = new CSVLoader((res) => {
    switchView("chart");
    state.currentStockSummary = res.chartData.summary;
    state.currentCode = res.chartData.summary.code;
    updateTickerHeader(res.chartData.summary);
    chartManager.setData(res.chartData, { indicators: res.indicators });
    diagnosticUI.render(res);
  });

  // Elements
  const searchInput = document.getElementById("search-input");
  const searchDropdown = document.getElementById("search-dropdown");
  const colorToggleBtn = document.getElementById("color-toggle-btn");
  const watchlistPinBtn = document.getElementById("watchlist-pin-btn");
  const loadingOverlay = document.getElementById("loading-overlay");
  const btnNavChart = document.getElementById("btn-nav-chart");
  const btnNavDash = document.getElementById("btn-nav-dash");
  const btnNavEtf = document.getElementById("btn-nav-etf");
  const chartViewWrapper = document.getElementById("chart-view-wrapper");
  const dashboardViewContainer = document.getElementById("dashboard-view-container");
  const etfDashboardViewContainer = document.getElementById("etf-dashboard-view-container");

  // View Switcher Function
  function switchView(view) {
    // Reset all nav buttons
    if (btnNavChart) btnNavChart.classList.remove("active");
    if (btnNavDash) btnNavDash.classList.remove("active");
    if (btnNavEtf) btnNavEtf.classList.remove("active");

    // Hide all view containers
    if (chartViewWrapper) chartViewWrapper.style.display = "none";
    if (dashboardViewContainer) dashboardViewContainer.classList.remove("active");
    if (etfDashboardViewContainer) etfDashboardViewContainer.classList.remove("active");

    if (view === "dash") {
      if (btnNavDash) btnNavDash.classList.add("active");
      if (dashboardViewContainer) dashboardViewContainer.classList.add("active");
      dashboardUI.load();
    } else if (view === "etf") {
      if (btnNavEtf) btnNavEtf.classList.add("active");
      if (etfDashboardViewContainer) etfDashboardViewContainer.classList.add("active");
      etfDashboardUI.load();
    } else {
      if (btnNavChart) btnNavChart.classList.add("active");
      if (chartViewWrapper) chartViewWrapper.style.display = "flex";
      // Force charts resize
      setTimeout(() => {
        window.dispatchEvent(new Event("resize"));
      }, 50);
    }
  }

  if (btnNavChart) btnNavChart.addEventListener("click", () => switchView("chart"));
  if (btnNavDash) btnNavDash.addEventListener("click", () => switchView("dash"));
  if (btnNavEtf) btnNavEtf.addEventListener("click", () => switchView("etf"));

  // Mobile Bottom Navigation Switcher
  const mobileNavBtns = document.querySelectorAll(".mobile-nav-btn");
  const leftSidebar = document.querySelector(".left-sidebar");
  const rightPanel = document.querySelector(".right-panel");

  function setMobileActiveTab(tabName) {
    mobileNavBtns.forEach(b => {
      if (b.dataset.tab === tabName) b.classList.add("active");
      else b.classList.remove("active");
    });
  }

  function resetMobilePanels() {
    if (leftSidebar) leftSidebar.classList.remove("mobile-active");
    if (rightPanel) rightPanel.classList.remove("mobile-active");
  }

  mobileNavBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.tab;
      setMobileActiveTab(tab);

      if (tab === "dash") {
        resetMobilePanels();
        switchView("dash");
      } else if (tab === "etf") {
        resetMobilePanels();
        switchView("etf");
      } else {
        switchView("chart");
        if (tab === "chart") {
          resetMobilePanels();
          setTimeout(() => window.dispatchEvent(new Event("resize")), 60);
        } else if (tab === "diag") {
          resetMobilePanels();
          if (rightPanel) rightPanel.classList.add("mobile-active");
          const diagTabBtn = document.querySelector('.right-tab-btn[data-target="diagnostic-tab-content"]');
          if (diagTabBtn) diagTabBtn.click();
        } else if (tab === "watch") {
          resetMobilePanels();
          if (leftSidebar) leftSidebar.classList.add("mobile-active");
        } else if (tab === "screen") {
          resetMobilePanels();
          if (rightPanel) rightPanel.classList.add("mobile-active");
          const screenTabBtn = document.querySelector('.right-tab-btn[data-target="screener-tab-content"]');
          if (screenTabBtn) screenTabBtn.click();
        }
      }
    });
  });

  // Quick Chips
  document.querySelectorAll(".quick-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const code = chip.dataset.code;
      if (code) {
        setMobileActiveTab("chart");
        resetMobilePanels();
        switchView("chart");
        loadStock(code);
      }
    });
  });

  // 1. Load Stock Core Function
  async function loadStock(code, customInterval, customRange) {
    if (state.isLoading) return;
    setLoading(true);

    state.currentCode = code;
    if (customInterval) state.interval = customInterval;
    if (customRange) state.range = customRange;

    try {
      // 1-call fast fetch: /api/stock/{code} contains summary, candles, indicators, and diagnosis
      const chartData = await API.getStockData(state.currentCode, state.interval, state.range);

      let diagData = chartData;
      let indicatorsData = chartData;

      // Graceful fallback if indicators or diagnosis not present in payload
      if (!chartData.indicators || !chartData.diagnosis) {
        try {
          const [dData, iData] = await Promise.all([
            API.getDiagnosis(state.currentCode, state.interval, state.range),
            API.getIndicators(state.currentCode, state.interval, state.range)
          ]);
          diagData = dData;
          indicatorsData = iData;
        } catch (e) {
          console.warn("Secondary indicators fetch error:", e);
        }
      }

      state.currentStockSummary = chartData.summary;

      // Update Ticker Header
      updateTickerHeader(chartData.summary);

      // Render Charts
      chartManager.setData(chartData, indicatorsData);

      // Render Diagnosis
      diagnosticUI.render(diagData);

      // Update Watchlist and Backtest
      watchlistManager.setCurrentStock(state.currentCode);
      backtestUI.setStock(state.currentCode);

      if (chartData.summary && chartData.summary.notice) {
        if (window.Toast) window.Toast.warning(chartData.summary.notice);
      } else if (window.Toast && window.innerWidth < 768) {
        window.Toast.info(`已載入 ${chartData.summary.name} (${chartData.summary.code})`);
      }

    } catch (err) {
      console.error("載入股票失敗:", err);
      const errMsg = err.message || "網路連線異常或代碼無效";
      if (window.Toast) {
        window.Toast.error(`載入股票失敗: ${errMsg}`);
      }

      // Friendly UI update so page doesn't remain stuck on "數據連線中..."
      const nameEl = document.getElementById("stock-name");
      if (nameEl) nameEl.textContent = `無法連線 (${state.currentCode})`;
      const legendEl = document.getElementById("chart-legend-box");
      if (legendEl) {
        legendEl.innerHTML = `
          <div class="legend-item">
            <span class="legend-label" style="color:#ff4d4f; font-weight:700;">⚠️ 數據連線失敗: ${errMsg}</span>
            <button id="btn-chart-retry" style="margin-left:12px; background:var(--color-accent); color:#fff; border:none; border-radius:4px; padding:3px 10px; font-size:12px; cursor:pointer; font-weight:600;">🔄 立即重試</button>
          </div>
        `;
        const retryBtn = document.getElementById("btn-chart-retry");
        if (retryBtn) retryBtn.addEventListener("click", () => loadStock(state.currentCode));
      }
    } finally {
      setLoading(false);
    }
  }

  // Helper for safe number display
  const fmtNum = (val, digits = 2) => (typeof val === "number" && !isNaN(val)) ? val.toFixed(digits) : "--";

  // 2. Update Ticker Bar Header
  function updateTickerHeader(summary) {
    if (!summary) return;

    document.getElementById("stock-name").textContent = summary.name || "----";
    document.getElementById("stock-code").textContent = summary.code || "----";
    document.getElementById("stock-market").textContent = summary.market || "TWSE";
    document.getElementById("stock-industry").textContent = summary.industry || "台股";

    const priceEl = document.getElementById("current-price");
    const changeEl = document.getElementById("price-change");
    const changePctEl = document.getElementById("price-change-pct");

    priceEl.textContent = fmtNum(summary.regularMarketPrice, 2);

    const isUp = (summary.change || 0) >= 0;
    const sign = isUp ? "+" : "";

    // Determine color class based on mode
    const colorClass = isUp 
      ? (state.isTaiwanColor ? "up-text" : "down-text")
      : (state.isTaiwanColor ? "down-text" : "up-text");

    priceEl.className = `current-price ${colorClass}`;
    changeEl.className = `price-change-box ${colorClass}`;

    changeEl.textContent = `${sign}${fmtNum(summary.change, 2)}`;
    changePctEl.textContent = `(${sign}${fmtNum(summary.changePercent, 2)}%)`;

    // Limit prices
    document.getElementById("limit-up-price").textContent = fmtNum(summary.limitUp, 2);
    document.getElementById("limit-down-price").textContent = fmtNum(summary.limitDown, 2);

    // Metrics
    document.getElementById("metric-open").textContent = fmtNum(summary.open, 2);
    document.getElementById("metric-high").textContent = fmtNum(summary.high, 2);
    document.getElementById("metric-low").textContent = fmtNum(summary.low, 2);
    document.getElementById("metric-prev-close").textContent = fmtNum(summary.previousClose, 2);
    document.getElementById("metric-volume-lots").textContent = typeof summary.volumeLots === "number" ? `${summary.volumeLots.toLocaleString()} 張` : "-- 張";

    // Fundamentals (PE, PB, Yield) & ETF Specifics
    const peEl = document.getElementById("stock-pe");
    const pbEl = document.getElementById("stock-pb");
    const yieldEl = document.getElementById("stock-yield");
    const trustTagEl = document.getElementById("stock-trust-tag");
    const etfPremEl = document.getElementById("stock-etf-prem");
    const etfNavEl = document.getElementById("stock-etf-nav");
    const etfSpreadEl = document.getElementById("stock-etf-spread");

    const isETF = !!(summary.etf || (summary.code && summary.code.startsWith("00")));

    if (isETF && summary.etf) {
      // Show ETF specific badges and hide standard stock PE/PB
      if (peEl) peEl.style.display = "none";
      if (pbEl) pbEl.style.display = "none";

      if (etfPremEl) {
        etfPremEl.style.display = "inline-flex";
        const prem = summary.etf.premiumDiscountPercent || 0;
        const pSign = prem > 0 ? "+" : "";
        const pStatus = prem < -0.4 ? "折價" : (prem > 0.4 ? "溢價" : "折溢價");
        etfPremEl.textContent = `${pStatus} ${pSign}${prem.toFixed(2)}%`;
        etfPremEl.className = "badge-tag etf-prem-tag";
        if (prem < -0.4) etfPremEl.classList.add("etf-prem-discount");
        else if (prem > 0.8) etfPremEl.classList.add("etf-prem-severe");
        else if (prem > 0.4) etfPremEl.classList.add("etf-prem-premium");
        else etfPremEl.classList.add("etf-prem-normal");
      }

      if (etfNavEl) {
        etfNavEl.style.display = "inline-flex";
        etfNavEl.textContent = summary.etf.nav ? `淨值 ${summary.etf.nav.toFixed(2)} 元` : "淨值 --";
      }

      if (etfSpreadEl) {
        etfSpreadEl.style.display = "inline-flex";
        if (summary.etf.spreadPercent !== null && summary.etf.spreadPercent !== undefined) {
          etfSpreadEl.textContent = `價差 ${summary.etf.spread} (${summary.etf.spreadPercent}%)`;
        } else {
          etfSpreadEl.textContent = "五檔即時撮合";
        }
      }
    } else {
      // Show standard PE / PB badges
      if (peEl) {
        peEl.style.display = "inline-flex";
        peEl.textContent = summary.peRatio ? `PE ${summary.peRatio}x` : "PE --";
      }
      if (pbEl) {
        pbEl.style.display = "inline-flex";
        pbEl.textContent = summary.pbRatio ? `PB ${summary.pbRatio}x` : "PB --";
      }
      if (etfPremEl) etfPremEl.style.display = "none";
      if (etfNavEl) etfNavEl.style.display = "none";
      if (etfSpreadEl) etfSpreadEl.style.display = "none";
    }

    if (yieldEl) {
      if (summary.dividendYield !== null && summary.dividendYield !== undefined) {
        yieldEl.textContent = `殖利率 ${summary.dividendYield}%`;
        yieldEl.classList.toggle("high-yield", summary.dividendYield >= 4.0);
      } else {
        yieldEl.textContent = "殖利率 --%";
        yieldEl.classList.remove("high-yield");
      }
    }

    // Institutional Metrics
    const inst = summary.institutional;
    if (trustTagEl) {
      if (inst && inst.isTrustFocus) {
        trustTagEl.style.display = "inline-flex";
        trustTagEl.textContent = `🔥 投信連買 ${inst.trustConsecutiveDays} 日 (作帳認養)`;
      } else {
        trustTagEl.style.display = "none";
      }
    }

    const instTotalEl = document.getElementById("metric-inst-total");
    const foreignEl = document.getElementById("metric-foreign-lots");
    const trustEl = document.getElementById("metric-trust-lots");

    if (inst) {
      if (instTotalEl) {
        const tSign = inst.totalLots > 0 ? "+" : "";
        instTotalEl.textContent = `${tSign}${inst.totalLots.toLocaleString()} 張`;
        instTotalEl.className = `metric-value ${inst.totalLots >= 0 ? (state.isTaiwanColor ? "up-text" : "down-text") : (state.isTaiwanColor ? "down-text" : "up-text")}`;
      }
      if (foreignEl) {
        const fSign = inst.foreignLots > 0 ? "+" : "";
        foreignEl.textContent = `${fSign}${inst.foreignLots.toLocaleString()}`;
        foreignEl.style.color = inst.foreignLots >= 0 ? "var(--color-up)" : "var(--color-down)";
      }
      if (trustEl) {
        const trSign = inst.trustLots > 0 ? "+" : "";
        trustEl.textContent = `${trSign}${inst.trustLots.toLocaleString()}`;
        trustEl.style.color = inst.trustLots >= 0 ? "#b37feb" : "#8c8c8c";
      }
    }

    watchlistManager.updatePinButton(summary.code);
  }

  // 3. Setup Timeframe buttons
  const timeframeBtns = document.querySelectorAll(".timeframe-btn");
  timeframeBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      timeframeBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      const interval = btn.dataset.interval;
      let range = "1y";
      if (interval === "5m" || interval === "15m") range = "5d";
      else if (interval === "60m") range = "1mo";
      else if (interval === "1wk") range = "2y";
      else if (interval === "1mo") range = "5y";

      loadStock(state.currentCode, interval, range);
    });
  });

  // 4. Setup Overlay Checkboxes (MA & Bollinger)
  document.querySelectorAll(".overlay-checkbox").forEach(cb => {
    cb.addEventListener("change", (e) => {
      const key = e.target.dataset.overlay;
      if (key) {
        chartManager.setOverlayVisibility(key, e.target.checked);
      }
    });
  });

  // Fibonacci & Support/Resistance Toggle
  const fibToggle = document.getElementById("fibonacci-toggle");
  if (fibToggle) {
    fibToggle.addEventListener("change", (e) => {
      chartManager.toggleFibonacci(e.target.checked);
      if (e.target.checked) {
        Toast.show("📐 已繪製自動支撐壓力與斐波那契黃金分割線", "info");
      }
    });
  }

  // 5. Setup Sub-indicator Tabs
  const subTabs = document.querySelectorAll(".sub-tab-btn");
  subTabs.forEach(btn => {
    btn.addEventListener("click", () => {
      subTabs.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const ind = btn.dataset.indicator;
      chartManager.setSubIndicator(ind);
    });
  });

  // 6. Color Scheme Toggle (Taiwan vs International)
  colorToggleBtn.addEventListener("click", () => {
    state.isTaiwanColor = !state.isTaiwanColor;
    document.body.classList.toggle("mode-international", !state.isTaiwanColor);

    if (state.isTaiwanColor) {
      colorToggleBtn.innerHTML = `<span>🇹🇼</span><span>台股 (紅漲綠跌)</span>`;
      if (window.Toast) window.Toast.info("已切換為：🇹🇼 台股模式 (紅漲綠跌)");
    } else {
      colorToggleBtn.innerHTML = `<span>🌐</span><span>國際 (綠漲紅跌)</span>`;
      if (window.Toast) window.Toast.info("已切換為：🌐 國際模式 (綠漲紅跌)");
    }

    chartManager.setTaiwanColorMode(state.isTaiwanColor);
    if (state.currentStockSummary) {
      updateTickerHeader(state.currentStockSummary);
    }
  });

  // 7. Watchlist Pin/Unpin Button
  watchlistPinBtn.addEventListener("click", () => {
    if (state.currentStockSummary) {
      const wasPinned = watchlistManager.isPinned(state.currentStockSummary.code);
      watchlistManager.togglePin(state.currentStockSummary);
      const isNowPinned = watchlistManager.isPinned(state.currentStockSummary.code);
      resetMobilePanels();
      if (window.Toast) {
        if (isNowPinned) {
          window.Toast.success(`⭐ 已將 ${state.currentStockSummary.name} 加入自選股`);
        } else {
          window.Toast.info(`已將 ${state.currentStockSummary.name} 移出自選股`);
        }
      }
    }
  });

  // 8. Search Input & Autocomplete Dropdown
  let searchDebounceTimer = null;
  searchInput.addEventListener("input", (e) => {
    const val = e.target.value.trim();
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(async () => {
      if (!val) {
        searchDropdown.classList.remove("active");
        return;
      }
      try {
        const data = await API.searchStocks(val);
        const list = data.results || [];
        if (list.length === 0) {
          searchDropdown.innerHTML = `<div style="padding:14px; text-align:center; color:var(--text-muted); font-size:12px;">無符合標的，請輸入純代號或完整名稱</div>`;
        } else {
          let html = "";
          list.forEach(item => {
            html += `
              <div class="search-item" data-code="${item.code}">
                <div class="search-item-left">
                  <span class="search-item-code">${item.code}</span>
                  <span class="search-item-name">${item.name}</span>
                </div>
                <div class="search-item-right">
                  <span class="search-item-industry">${item.industry || ''}</span>
                  <span class="search-item-market">${item.market || 'TWSE'}</span>
                </div>
              </div>
            `;
          });
          searchDropdown.innerHTML = html;

          searchDropdown.querySelectorAll(".search-item").forEach(el => {
            el.addEventListener("click", () => {
              const code = el.dataset.code;
              searchInput.value = "";
              searchDropdown.classList.remove("active");
              setMobileActiveTab("chart");
              resetMobilePanels();
              switchView("chart");
              loadStock(code);
            });
          });
        }
      } catch (err) {
        searchDropdown.innerHTML = `<div style="padding:14px; text-align:center; color:#ff4d4f; font-size:12px;">搜尋失敗: ${err.message}</div>`;
      }
      searchDropdown.classList.add("active");
    }, 200);
  });

  // Enter to search direct code
  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const val = searchInput.value.trim();
      if (val) {
        searchDropdown.classList.remove("active");
        searchInput.value = "";
        setMobileActiveTab("chart");
        resetMobilePanels();
        switchView("chart");
        loadStock(val.toUpperCase());
      }
    } else if (e.key === "Escape") {
      searchDropdown.classList.remove("active");
    }
  });

  // Global "/" shortcut to focus search
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement !== searchInput) {
      e.preventDefault();
      searchInput.focus();
    }
  });

  // Hide dropdown on click outside
  document.addEventListener("click", (e) => {
    if (!searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
      searchDropdown.classList.remove("active");
    }
  });

  // 9. Left Panel Tabs (Watchlist vs Categories)
  const leftTabs = document.querySelectorAll(".left-tab-btn");
  leftTabs.forEach(btn => {
    btn.addEventListener("click", () => {
      leftTabs.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      document.querySelectorAll(".left-tab-content").forEach(c => c.classList.remove("active"));
      const targetId = btn.dataset.target;
      document.getElementById(targetId)?.classList.add("active");
    });
  });

  // 10. Right Panel Tabs (Diagnostics vs Screener vs Backtest)
  const rightTabs = document.querySelectorAll(".right-tab-btn");
  rightTabs.forEach(btn => {
    btn.addEventListener("click", () => {
      rightTabs.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      document.querySelectorAll(".right-tab-content").forEach(c => c.classList.remove("active"));
      const targetId = btn.dataset.target;
      document.getElementById(targetId)?.classList.add("active");
      if (targetId === "screener-tab-content" && screenerUI) {
        screenerUI.ensureScanned();
      }
    });
  });

  function setLoading(loading) {
    state.isLoading = loading;
    loadingOverlay.classList.toggle("active", loading);
  }

  // Initial Load with 2330 台積電
  loadStock("2330");
});
