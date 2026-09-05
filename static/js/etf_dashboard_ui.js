/**
 * ETF Dashboard UI Module - Custom Watchlist & Real-Time Technical Monitoring
 * Monitors MA5/MA20/MA60, MACD, KD(9,3,3), RSI(6), Premium/Discount, and Real-Time NAV.
 */

class EtfDashboardUI {
  constructor(containerId, onSelectStock) {
    this.container = document.getElementById(containerId);
    this.onSelectStock = onSelectStock;
    this.isLoading = false;

    this.defaultEtfs = [
      "0050", "0056", "00878", "00919", "00929", "006208",
      "00713", "00940", "00679B", "00687B", "00937B", "00757"
    ];

    this.presetCategories = {
      all: { label: "全部自選", icon: "⭐", codes: null },
      market: { label: "旗艦市值", icon: "👑", codes: ["0050", "006208", "00692", "00905", "00922", "00923"] },
      high_div: { label: "高息優選", icon: "💰", codes: ["0056", "00878", "00919", "00929", "00713", "00940", "00915", "00918"] },
      bonds: { label: "債券首選", icon: "🏦", codes: ["00679B", "00687B", "00937B", "00720B", "00772B", "00751B"] },
      tech: { label: "科技半導體", icon: "🔬", codes: ["00881", "00830", "00891", "00892", "0052"] },
      global: { label: "全球海外", icon: "🌐", codes: ["00757", "00646", "00662", "00647L", "00648R"] }
    };

    this.activeCategory = "all";
    this.customList = this.loadCustomList();
  }

  loadCustomList() {
    try {
      const saved = localStorage.getItem("tw_stock_custom_etfs");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed.map(c => String(c).trim().toUpperCase());
        }
      }
    } catch (e) {
      console.warn("Failed to load custom ETF list from localStorage:", e);
    }
    return [...this.defaultEtfs];
  }

  saveCustomList() {
    try {
      localStorage.setItem("tw_stock_custom_etfs", JSON.stringify(this.customList));
    } catch (e) {
      console.warn("Failed to save custom ETF list:", e);
    }
  }

  getCurrentCodes() {
    if (this.activeCategory === "all") {
      return this.customList;
    }
    const cat = this.presetCategories[this.activeCategory];
    return cat && cat.codes ? cat.codes : this.customList;
  }

  formatUnits(val) {
    if (!val || val === "-" || val === "" || val === "0") return "";
    const num = parseFloat(String(val).replace(/,/g, ""));
    if (isNaN(num)) return val;
    const abs = Math.abs(num);
    const sign = num > 0 ? "+" : (num < 0 ? "-" : "");
    if (abs >= 100000000) {
      return `${sign}${(abs / 100000000).toFixed(2)} 億單位`;
    } else if (abs >= 10000) {
      return `${sign}${(abs / 10000).toFixed(1)} 萬單位`;
    }
    return `${sign}${num.toLocaleString()} 單位`;
  }

  async load() {
    if (!this.container) return;
    this.isLoading = true;

    this.container.innerHTML = `
      <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; padding:70px 20px; color:var(--color-accent); gap:14px;">
        <div class="spinner" style="width:40px; height:40px;"></div>
        <div style="font-size:15px; font-weight:700; color:var(--text-primary);">正在聯網獲取自選 ETF 即時折溢價、淨值、均線與指標動能...</div>
        <div style="font-size:12px; color:var(--text-muted);">整合台灣證券交易所 MIS 官方即時淨值與 6 個月 MA/MACD/KD/RSI 指標分析</div>
      </div>
    `;

    try {
      const codes = this.getCurrentCodes();
      const data = await API.getEtfDashboard(codes.join(","));
      this.render(data);
    } catch (err) {
      this.container.innerHTML = `
        <div style="text-align:center; padding:50px 20px; color:var(--color-up);">
          <div style="font-size:20px; margin-bottom:8px;">⚠️ 自選 ETF 看板載入失敗</div>
          <div style="font-size:13px; color:var(--text-muted); margin-bottom:16px;">${err.message || "伺服器處理逾時，請稍後重試"}</div>
          <button id="etf-retry-btn" class="color-toggle-btn" style="display:inline-flex;">🔄 重試載入</button>
        </div>
      `;
      const retryBtn = document.getElementById("etf-retry-btn");
      if (retryBtn) retryBtn.addEventListener("click", () => this.load());
    } finally {
      this.isLoading = false;
    }
  }

  render(data) {
    if (!this.container) return;

    const etfs = data.etfs || [];
    const count = data.etfCount || etfs.length;
    const maRatio = data.bullishMaRatio || 0;
    const macdRatio = data.positiveMacdRatio || 0;
    const kdRatio = data.bullishKdRatio || 0;
    const avgRsi = data.averageRsi || 50;
    const avgPrem = data.averagePremiumDiscount || 0;
    const discountCount = data.discountCount || 0;

    // Overall gauge color based on average premium/discount
    let premGaugeColor = "var(--color-accent)";
    let premMood = "合理市價區間";
    if (avgPrem < -0.3) {
      premGaugeColor = "var(--color-down)";
      premMood = "普遍折價偏甜 (安全邊際優)";
    } else if (avgPrem > 0.6) {
      premGaugeColor = "var(--color-up)";
      premMood = "整體偏高溢價 (留意追高)";
    }

    // Category Buttons HTML
    let categoryChipsHtml = "";
    Object.keys(this.presetCategories).forEach(k => {
      const cat = this.presetCategories[k];
      const isActive = this.activeCategory === k ? "active" : "";
      categoryChipsHtml += `
        <button class="etf-cat-btn ${isActive}" data-cat="${k}">
          <span>${cat.icon}</span>
          <span>${cat.label}</span>
          ${k === "all" ? `<span class="etf-cat-count">${this.customList.length}</span>` : ""}
        </button>
      `;
    });

    // ETF Cards HTML
    let cardsHtml = "";
    if (etfs.length === 0) {
      cardsHtml = `
        <div style="grid-column: 1 / -1; text-align:center; padding:60px 20px; background:var(--bg-secondary); border-radius:12px; border:1px dashed var(--border-color);">
          <div style="font-size:32px; margin-bottom:10px;">🪙</div>
          <div style="font-size:16px; font-weight:700; color:var(--text-primary); margin-bottom:6px;">目前自選清單為空</div>
          <div style="font-size:13px; color:var(--text-muted); margin-bottom:18px;">請使用上方搜尋框輸入 ETF 代碼（如 0050、00878、00919）加入，或點擊下方恢復預設熱門標的</div>
          <button id="etf-empty-reset-btn" class="color-toggle-btn" style="display:inline-flex;">⚡ 恢復預設熱門 ETF</button>
        </div>
      `;
    } else {
      etfs.forEach(item => {
        const isUp = item.change >= 0;
        const colorClass = isUp ? "up-text" : "down-text";
        const sign = isUp ? "+" : "";

        // Premium / Discount styling
        const pPct = item.etf.premiumDiscountPercent;
        let premBadgeClass = "prem-badge-fair";
        let premBadgeText = item.etf.label;
        if (pPct < -0.4) {
          premBadgeClass = "prem-badge-deep-disc";
        } else if (pPct < -0.1) {
          premBadgeClass = "prem-badge-mild-disc";
        } else if (pPct <= 0.3) {
          premBadgeClass = "prem-badge-fair";
        } else if (pPct <= 0.8) {
          premBadgeClass = "prem-badge-mild-prem";
        } else {
          premBadgeClass = "prem-badge-danger-prem";
        }

        // MA Badge
        let maBadgeColor = "#94a3b8";
        if (item.ma.status === "bullish") maBadgeColor = "var(--color-up)";
        else if (item.ma.status === "bearish") maBadgeColor = "var(--color-down)";
        else if (item.ma.status === "above_ma20") maBadgeColor = "var(--color-accent)";

        // MACD Badge
        const isMacdPos = item.macd.isPositive;
        const macdColor = isMacdPos ? "var(--color-up)" : "var(--color-down)";
        const macdLabel = isMacdPos ? `紅柱 (+${item.macd.bar.toFixed(2)})` : `綠柱 (${item.macd.bar.toFixed(2)})`;

        // KD Badge
        let kdBadgeColor = "var(--text-secondary)";
        if (item.kd.cross === "golden_cross") kdBadgeColor = "#ff7875";
        else if (item.kd.cross === "death_cross") kdBadgeColor = "#52c41a";
        else if (item.kd.isBullish) kdBadgeColor = "var(--color-accent)";

        // RSI Badge
        let rsiColor = "var(--text-secondary)";
        let rsiLabel = `${item.rsi.rsi6.toFixed(1)} · 常態`;
        if (item.rsi.status === "overbought") {
          rsiColor = "var(--color-up)";
          rsiLabel = `${item.rsi.rsi6.toFixed(1)} · 超買警戒 (>75)`;
        } else if (item.rsi.status === "oversold") {
          rsiColor = "var(--color-down)";
          rsiLabel = `${item.rsi.rsi6.toFixed(1)} · 超賣醞釀 (<25)`;
        } else if (item.rsi.status === "bull_zone") {
          rsiColor = "var(--color-accent)";
          rsiLabel = `${item.rsi.rsi6.toFixed(1)} · 強勢多方`;
        }

        cardsHtml += `
          <div class="dash-stock-card etf-stock-card" data-code="${item.code}">
            <!-- Header -->
            <div class="dash-card-header">
              <div style="flex:1;">
                <div style="display:flex; align-items:center; gap:8px;">
                  <span class="dash-stock-name">${item.name}</span>
                  <span class="dash-stock-code">${item.code}</span>
                  <button class="etf-remove-btn" title="從自選清單移除" data-code="${item.code}">&times;</button>
                </div>
                <div style="display:flex; align-items:center; gap:6px; margin-top:3px;">
                  <span class="badge-tag">${item.market}</span>
                  <span class="badge-tag">${item.industry || 'ETF'}</span>
                  ${item.volumeLots ? `<span style="font-size:11px; color:var(--text-muted);">${Number(item.volumeLots).toLocaleString()} 張</span>` : ''}
                </div>
              </div>

              <!-- Price Box -->
              <div class="dash-price-box">
                <div class="dash-price ${colorClass}">${item.price.toFixed(2)}</div>
                <div class="dash-change ${colorClass}">${sign}${item.change.toFixed(2)} (${sign}${item.changePercent.toFixed(2)}%)</div>
              </div>
            </div>

            <!-- Real-Time NAV & Premium / Discount Section (Official TWSE Section) -->
            <div class="etf-nav-strip">
              <div class="etf-nav-item">
                <span class="etf-nav-lbl">即時估計淨值 (NAV)</span>
                <span class="etf-nav-val">${item.etf.nav ? item.etf.nav.toFixed(2) + ' 元' : '--'}</span>
                ${item.etf.prevNav ? `<span style="font-size:10px; color:var(--text-muted); margin-top:1px;">前日公告: ${item.etf.prevNav.toFixed(2)} 元</span>` : ''}
              </div>
              <div class="etf-nav-item" style="text-align:right;">
                <span class="etf-nav-lbl">即時折溢價 (市價 vs 淨值)</span>
                <span class="etf-prem-badge ${premBadgeClass}">
                  ${premBadgeText}
                </span>
                <span style="font-size:10px; font-family:var(--font-mono); color:var(--text-muted); margin-top:2px;">
                  差額: ${item.etf.diff > 0 ? '+' : ''}${item.etf.diff.toFixed(2)} 元
                </span>
              </div>
            </div>

            <!-- Units & Official Source Disclosure -->
            ${(item.etf.issuedUnits || item.etf.diffUnits || item.etf.refUrl) ? `
              <div class="etf-units-strip">
                <div style="display:flex; align-items:center; gap:6px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                  <span class="etf-unit-dot"></span>
                  <span style="font-size:11px; color:var(--text-secondary);">
                    ${item.etf.issuedUnits ? `已發行: <b>${this.formatUnits(item.etf.issuedUnits)}</b>` : ''}
                    ${item.etf.diffUnits && item.etf.diffUnits !== '0' ? `<span style="margin-left:4px; color:${Number(String(item.etf.diffUnits).replace(/,/g,'')) > 0 ? 'var(--color-up)' : 'var(--color-down)'};">(${this.formatUnits(item.etf.diffUnits)})</span>` : ''}
                  </span>
                </div>
                ${item.etf.refUrl ? `
                  <a href="${item.etf.refUrl}" target="_blank" rel="noopener noreferrer" class="etf-ref-link" title="前往投信發行人官方即時淨值與申購買回清單 (PCF) 專區">
                    投信專區 ↗
                  </a>
                ` : ''}
              </div>
            ` : ''}

            <!-- Technical Indicator Checklist -->
            <div class="dash-card-indicators">
              <!-- MA5 / MA20 / MA60 -->
              <div class="dash-ind-row">
                <span class="dash-ind-label">均線排列 (MA5 / 20 / 60)</span>
                <span class="dash-ind-badge" style="color:${maBadgeColor}; border-color:${maBadgeColor}44; background:${maBadgeColor}11;">
                  ${item.ma.label}
                </span>
              </div>
              <div class="dash-ma-pills">
                <span>5MA: <b>${item.ma.ma5 ? item.ma.ma5.toFixed(2) : '--'}</b></span>
                <span>20MA: <b>${item.ma.ma20 ? item.ma.ma20.toFixed(2) : '--'}</b></span>
                <span>60MA: <b>${item.ma.ma60 ? item.ma.ma60.toFixed(2) : '--'}</b></span>
              </div>

              <!-- MACD (12, 26, 9) -->
              <div class="dash-ind-row" style="margin-top:8px;">
                <span class="dash-ind-label">MACD 柱狀動能 (OSC)</span>
                <span class="dash-ind-badge" style="color:${macdColor}; border-color:${macdColor}44; background:${macdColor}11;">
                  ${macdLabel}
                </span>
              </div>
              <div style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono); margin-bottom:4px;">
                DIF: ${item.macd.dif.toFixed(2)} | DEA: ${item.macd.dea.toFixed(2)}
              </div>

              <!-- KD (9, 3, 3) -->
              <div class="dash-ind-row" style="margin-top:6px;">
                <span class="dash-ind-label">KD (9, 3, 3) 交叉指標</span>
                <span class="dash-ind-badge" style="color:${kdBadgeColor}; border-color:${kdBadgeColor}44; background:${kdBadgeColor}11;">
                  ${item.kd.crossLabel}
                </span>
              </div>
              <div class="dash-ma-pills" style="margin-bottom:4px;">
                <span>K(9): <b>${item.kd.k.toFixed(1)}</b></span>
                <span>D(9): <b>${item.kd.d.toFixed(1)}</b></span>
                <span style="color:var(--text-muted); font-size:10px;">${item.kd.zoneLabel}</span>
              </div>

              <!-- RSI (6, 12) -->
              <div class="dash-ind-row" style="margin-top:6px;">
                <span class="dash-ind-label">RSI (6) 動能水位</span>
                <span class="dash-ind-badge" style="color:${rsiColor}; border-color:${rsiColor}44; background:${rsiColor}11;">
                  ${rsiLabel}
                </span>
              </div>
            </div>

            <!-- Footer: Timing & Deep Chart Link -->
            <div class="dash-card-footer">
              <div style="display:flex; align-items:center; gap:8px;">
                <div class="dash-mini-score" style="border-color:${item.actionColor}; color:${item.actionColor};">
                  ${item.score}
                </div>
                <div>
                  <div style="font-size:12px; font-weight:700; color:${item.actionColor};">${item.action}</div>
                </div>
              </div>
              <button class="dash-view-chart-btn" data-code="${item.code}">進入深度 K 線圖 ›</button>
            </div>
          </div>
        `;
      });
    }

    this.container.innerHTML = `
      <div class="dashboard-wrapper">
        <!-- Top ETF Pulse Banner -->
        <div class="market-pulse-card">
          <div class="pulse-left">
            <div class="temp-gauge-circle" style="border-color:${premGaugeColor}; box-shadow: 0 0 20px ${premGaugeColor}33;">
              <div class="temp-gauge-val" style="color:${premGaugeColor}; font-size:20px;">
                ${avgPrem > 0 ? '+' : ''}${avgPrem}%
              </div>
              <div class="temp-gauge-lbl">平均折溢價</div>
            </div>
            <div>
              <div style="font-size:12px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.5px;">ETF 市場定價與熱度指標</div>
              <div class="temp-mood-title" style="color:${premGaugeColor};">${premMood}</div>
              <div style="font-size:12px; color:var(--text-secondary); max-width:440px; line-height:1.4; margin-top:4px;">
                實時監控各熱門 ETF 官方最新估計淨值、折溢價幅度，結合 MA5/20/60 均線、MACD 柱狀動能與 KD/RSI 指標，掌握超值買點。
              </div>
            </div>
          </div>

          <div class="pulse-metrics-grid">
            <div class="pulse-metric-box">
              <div class="pulse-metric-label">均線多頭排列佔比</div>
              <div class="pulse-metric-val" style="color:var(--color-up);">${maRatio}%</div>
              <div style="font-size:10px; color:var(--text-muted);">MA5 > MA20 > MA60</div>
            </div>
            <div class="pulse-metric-box">
              <div class="pulse-metric-label">MACD 正柱 (紅柱) 佔比</div>
              <div class="pulse-metric-val" style="color:var(--color-accent);">${macdRatio}%</div>
              <div style="font-size:10px; color:var(--text-muted);">多方加速攻擊動能</div>
            </div>
            <div class="pulse-metric-box">
              <div class="pulse-metric-label">KD 多方 / 金叉佔比</div>
              <div class="pulse-metric-val" style="color:#ff85c0;">${kdRatio}%</div>
              <div style="font-size:10px; color:var(--text-muted);">K > D 或低檔起漲</div>
            </div>
            <div class="pulse-metric-box">
              <div class="pulse-metric-label">超值折價標的</div>
              <div class="pulse-metric-val" style="color:var(--color-down);">${discountCount} 檔</div>
              <div style="font-size:10px; color:var(--text-muted);">市價低於淨值 (安全邊際)</div>
            </div>
          </div>
        </div>

        <!-- ETF Custom Controls Bar -->
        <div class="etf-control-panel">
          <!-- Quick Category Filters -->
          <div class="etf-categories-bar">
            ${categoryChipsHtml}
          </div>

          <!-- Add ETF Form & Actions -->
          <div class="etf-action-tools">
            <div class="etf-add-input-wrapper">
              <input type="text" id="etf-add-input" placeholder="輸入 ETF 代碼 (如: 00935, 00881)..." maxlength="10">
              <button id="etf-add-btn" class="etf-btn-add">＋ 加入自選</button>
            </div>
            <button id="etf-reset-btn" class="color-toggle-btn" title="恢復預設熱門台股 ETF 清單" style="font-size:12px; padding:6px 12px;">
              ⚡ 恢復預設
            </button>
            <button id="etf-refresh-btn" class="color-toggle-btn" title="重新獲取實時行情與淨值" style="font-size:12px; padding:6px 12px;">
              🔄 重新整理
            </button>
          </div>
        </div>

        <!-- Section Title -->
        <div class="dash-section-header">
          <div>
            <div style="font-size:16px; font-weight:700; color:var(--text-primary);">
              ${this.presetCategories[this.activeCategory]?.label || '自選'} ETF 實時技術與折溢價矩陣
              <span style="font-size:12px; font-weight:500; color:var(--text-muted); margin-left:8px;">(共 ${count} 檔)</span>
            </div>
            <div style="font-size:12px; color:var(--text-muted);">
              監控項目：市價、即時淨值 (NAV)、折溢價差額與比率、MA5/MA20/MA60 排列、MACD 動能、KD(9,3,3)、RSI(6) 水位
            </div>
          </div>
        </div>

        <!-- ETF Cards Grid -->
        <div class="dash-stocks-grid etf-stocks-grid">
          ${cardsHtml}
        </div>
      </div>
    `;

    this.bindEvents();
  }

  bindEvents() {
    // 1. View deep chart on card / button click
    this.container.querySelectorAll(".dash-view-chart-btn, .etf-stock-card").forEach(el => {
      el.addEventListener("click", (e) => {
        // Ignore if clicking remove button
        if (e.target.closest(".etf-remove-btn")) return;
        const code = el.dataset.code || el.closest(".etf-stock-card")?.dataset.code;
        if (code && this.onSelectStock) {
          this.onSelectStock(code);
        }
      });
    });

    // 2. Remove ETF from custom list
    this.container.querySelectorAll(".etf-remove-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const code = btn.dataset.code;
        if (!code) return;
        this.removeCode(code);
      });
    });

    // 3. Category Filter Buttons
    this.container.querySelectorAll(".etf-cat-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const cat = btn.dataset.cat;
        if (cat && cat !== this.activeCategory) {
          this.activeCategory = cat;
          this.load();
        }
      });
    });

    // 4. Add ETF Input & Button
    const addInput = document.getElementById("etf-add-input");
    const addBtn = document.getElementById("etf-add-btn");
    const handleAdd = () => {
      if (!addInput) return;
      const raw = addInput.value.trim().toUpperCase();
      if (!raw) {
        if (window.Toast) Toast.warning("請輸入 ETF 代碼 (例如: 00935)");
        return;
      }
      this.addCode(raw);
      addInput.value = "";
    };

    if (addBtn) addBtn.addEventListener("click", handleAdd);
    if (addInput) {
      addInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") handleAdd();
      });
    }

    // 5. Reset button
    const resetBtn = document.getElementById("etf-reset-btn");
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        this.customList = [...this.defaultEtfs];
        this.saveCustomList();
        this.activeCategory = "all";
        if (window.Toast) Toast.success("已恢復預設熱門 ETF 清單");
        this.load();
      });
    }

    const emptyResetBtn = document.getElementById("etf-empty-reset-btn");
    if (emptyResetBtn) {
      emptyResetBtn.addEventListener("click", () => {
        this.customList = [...this.defaultEtfs];
        this.saveCustomList();
        this.activeCategory = "all";
        this.load();
      });
    }

    // 6. Refresh button
    const refreshBtn = document.getElementById("etf-refresh-btn");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => this.load());
    }
  }

  addCode(code) {
    const clean = code.split(".")[0].trim().toUpperCase();
    if (this.customList.includes(clean)) {
      if (window.Toast) Toast.info(`ETF ${clean} 已在自選清單中`);
      return;
    }
    this.customList.unshift(clean);
    this.saveCustomList();
    this.activeCategory = "all";
    if (window.Toast) Toast.success(`成功將 ETF ${clean} 加入自選`);
    this.load();
  }

  removeCode(code) {
    const clean = code.split(".")[0].trim().toUpperCase();
    this.customList = this.customList.filter(c => c !== clean);
    this.saveCustomList();
    if (window.Toast) Toast.info(`已從自選清單移除 ${clean}`);
    this.load();
  }
}
