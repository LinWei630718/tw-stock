/**
 * TradingView Lightweight Charts Manager
 * Handles Main Candlestick Chart, Overlays (MA, Bollinger), and Sub-indicator charts (Volume, KD, MACD, RSI, BIAS)
 */

class ChartManager {
  constructor(mainContainerId, subContainerId, legendContainerId) {
    this.mainContainer = document.getElementById(mainContainerId);
    this.subContainer = document.getElementById(subContainerId);
    this.legendContainer = document.getElementById(legendContainerId);

    this.isTaiwanColor = true; // True: Red up, Green down; False: Green up, Red down
    this.activeSubIndicator = "macd"; // macd, volume, rsi, kd, bias
    this.overlayVisibility = {
      ma5: true,
      ma10: false,
      ma20: true,
      ma60: true,
      ma120: false,
      ma240: false,
      bb: false
    };

    this.currentData = null;
    this.currentIndicators = null;

    this.mainChart = null;
    this.subChart = null;

    this.candleSeries = null;
    this.maSeries = {};
    this.bbSeries = {};

    this.subSeries = {};

    this.fibonacciLines = [];
    this.showFibonacci = false;
    this.tradeMarkers = [];

    this.initCharts();
    this.bindWindowResize();
  }

  getColorTheme() {
    const upColor = this.isTaiwanColor ? "#ff4d4f" : "#00b96b";
    const downColor = this.isTaiwanColor ? "#00b96b" : "#ff4d4f";
    return { upColor, downColor };
  }

  initCharts() {
    const { upColor, downColor } = this.getColorTheme();

    const chartOptions = {
      layout: {
        background: { color: "#0b0e14" },
        textColor: "#94a3b8",
        fontSize: 11,
        fontFamily: "'JetBrains Mono', 'Roboto Mono', monospace"
      },
      grid: {
        vertLines: { color: "rgba(255, 255, 255, 0.04)" },
        horzLines: { color: "rgba(255, 255, 255, 0.04)" }
      },
      crosshair: {
        mode: 1, // CrosshairMode.Normal
        vertLine: {
          color: "rgba(0, 180, 216, 0.4)",
          width: 1,
          style: 3 // LineStyle.Dashed
        },
        horzLine: {
          color: "rgba(0, 180, 216, 0.4)",
          width: 1,
          style: 3
        }
      },
      timeScale: {
        borderColor: "rgba(255, 255, 255, 0.08)",
        timeVisible: true,
        secondsVisible: false
      },
      rightPriceScale: {
        borderColor: "rgba(255, 255, 255, 0.08)",
        autoScale: true
      }
    };

    // 1. Create Main Chart
    const mainW = Math.max(this.mainContainer.clientWidth || 0, 400);
    const mainH = Math.max(this.mainContainer.clientHeight || 0, 350);
    this.mainChart = LightweightCharts.createChart(this.mainContainer, {
      ...chartOptions,
      width: mainW,
      height: mainH
    });

    // Candlestick Series
    this.candleSeries = this.mainChart.addCandlestickSeries({
      upColor: upColor,
      downColor: downColor,
      borderUpColor: upColor,
      borderDownColor: downColor,
      wickUpColor: upColor,
      wickDownColor: downColor
    });

    // Moving Average Lines
    const maConfigs = [
      { key: "ma5", color: "#fadb14", title: "MA5" },
      { key: "ma10", color: "#fa8c16", title: "MA10" },
      { key: "ma20", color: "#13c2c2", title: "MA20" },
      { key: "ma60", color: "#722ed1", title: "MA60" },
      { key: "ma120", color: "#eb2f96", title: "MA120" },
      { key: "ma240", color: "#52c41a", title: "MA240" }
    ];

    maConfigs.forEach(({ key, color, title }) => {
      this.maSeries[key] = this.mainChart.addLineSeries({
        color: color,
        lineWidth: 1.5,
        title: title,
        visible: this.overlayVisibility[key]
      });
    });

    // Bollinger Bands Lines
    this.bbSeries.upper = this.mainChart.addLineSeries({
      color: "rgba(24, 144, 255, 0.8)",
      lineWidth: 1,
      lineStyle: 2, // LineStyle.Dotted
      title: "BB Upper",
      visible: this.overlayVisibility.bb
    });
    this.bbSeries.middle = this.mainChart.addLineSeries({
      color: "rgba(24, 144, 255, 0.5)",
      lineWidth: 1,
      title: "BB Mid",
      visible: this.overlayVisibility.bb
    });
    this.bbSeries.lower = this.mainChart.addLineSeries({
      color: "rgba(24, 144, 255, 0.8)",
      lineWidth: 1,
      lineStyle: 2,
      title: "BB Lower",
      visible: this.overlayVisibility.bb
    });

    // 2. Create Sub-Chart
    const subW = Math.max(this.subContainer.clientWidth || 0, 400);
    const subH = Math.max(this.subContainer.clientHeight || 0, 150);
    this.subChart = LightweightCharts.createChart(this.subContainer, {
      ...chartOptions,
      width: subW,
      height: subH
    });

    // Synchronize Time Scales between Main Chart and Sub Chart (with re-entrance guard)
    let isSyncing = false;
    this.mainChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
      if (range && !isSyncing) {
        isSyncing = true;
        this.subChart.timeScale().setVisibleLogicalRange(range);
        isSyncing = false;
      }
    });
    this.subChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
      if (range && !isSyncing) {
        isSyncing = true;
        this.mainChart.timeScale().setVisibleLogicalRange(range);
        isSyncing = false;
      }
    });

    // Crosshair legend update
    this.mainChart.subscribeCrosshairMove(param => this.updateLegend(param));
  }

  setTaiwanColorMode(isTaiwan) {
    this.isTaiwanColor = isTaiwan;
    const { upColor, downColor } = this.getColorTheme();

    if (this.candleSeries) {
      this.candleSeries.applyOptions({
        upColor: upColor,
        downColor: downColor,
        borderUpColor: upColor,
        borderDownColor: downColor,
        wickUpColor: upColor,
        wickDownColor: downColor
      });
    }

    // Refresh sub indicator if volume or macd
    if (this.activeSubIndicator === "volume" || this.activeSubIndicator === "macd") {
      this.renderSubIndicator(this.activeSubIndicator);
    }
  }

  setOverlayVisibility(key, visible) {
    this.overlayVisibility[key] = visible;
    if (this.maSeries[key]) {
      this.maSeries[key].applyOptions({ visible });
    } else if (key === "bb") {
      this.bbSeries.upper.applyOptions({ visible });
      this.bbSeries.middle.applyOptions({ visible });
      this.bbSeries.lower.applyOptions({ visible });
    }
  }

  setData(stockData, indicatorsData) {
    this.currentData = stockData;
    this.currentIndicators = (indicatorsData && indicatorsData.indicators) ? indicatorsData.indicators : (stockData.indicators || {});

    // Ensure charts match current container geometry
    this.resizeCharts();

    const candles = stockData.candles || [];
    if (!candles.length) return;

    // Cache previous close for each candle to calculate accurate price change
    this.candlePrevCloseMap = new Map();
    for (let i = 0; i < candles.length; i++) {
      const c = candles[i];
      const prevC = i > 0 ? candles[i - 1].close : c.open;
      this.candlePrevCloseMap.set(c.time, prevC);
    }

    // Set Candlesticks
    this.candleSeries.setData(candles);

    // Set MA lines
    const ma = this.currentIndicators.ma || {};
    Object.keys(this.maSeries).forEach(key => {
      if (ma[key]) {
        this.maSeries[key].setData(ma[key]);
      }
    });

    // Set Bollinger Bands
    const bb = this.currentIndicators.bollinger || {};
    if (bb.upper && bb.middle && bb.lower) {
      this.bbSeries.upper.setData(bb.upper);
      this.bbSeries.middle.setData(bb.middle);
      this.bbSeries.lower.setData(bb.lower);
    }

    // Render Sub-indicator
    this.renderSubIndicator(this.activeSubIndicator);

    // Auto-fit content
    this.mainChart.timeScale().fitContent();
    this.subChart.timeScale().fitContent();

    // Default legend with latest candle
    this.updateLegendWithLatest();

    // Update MA5 / MA20 / MA60 alignment badge
    this.updateMAAlignmentBadge();

    // Re-render Fibonacci lines if toggled ON
    if (this.showFibonacci) {
      this.renderFibonacciLines();
    } else {
      this.clearFibonacciLines();
    }

    // Update markers (dividends + trade markers)
    this.updateMarkers();
  }

  updateMarkers() {
    if (!this.candleSeries) return;
    const combinedMarkers = [];

    // 1. Add Dividend Markers if available
    if (this.currentData && this.currentData.dividends) {
      this.currentData.dividends.forEach(d => {
        combinedMarkers.push({
          time: d.time,
          position: "belowBar",
          color: "#fadb14",
          shape: "circle",
          text: `D 配息${d.amount}元`
        });
      });
    }

    // 2. Add Backtest Trade Markers
    if (this.tradeMarkers && this.tradeMarkers.length) {
      combinedMarkers.push(...this.tradeMarkers);
    }

    // Sort markers by time
    combinedMarkers.sort((a, b) => (a.time > b.time ? 1 : -1));

    try {
      this.candleSeries.setMarkers(combinedMarkers);
    } catch (e) {
      console.warn("Failed to set markers:", e);
    }
  }

  toggleFibonacci(show) {
    this.showFibonacci = show;
    if (show) {
      this.renderFibonacciLines();
    } else {
      this.clearFibonacciLines();
    }
  }

  clearFibonacciLines() {
    if (this.candleSeries && this.fibonacciLines && this.fibonacciLines.length) {
      this.fibonacciLines.forEach(line => {
        try {
          this.candleSeries.removePriceLine(line);
        } catch (e) {}
      });
    }
    this.fibonacciLines = [];
  }

  renderFibonacciLines() {
    this.clearFibonacciLines();
    if (!this.candleSeries || !this.currentIndicators || !this.currentIndicators.fibonacci) return;
    const fib = this.currentIndicators.fibonacci;
    const levels = fib.levels || [];
    levels.forEach(lvl => {
      try {
        const line = this.candleSeries.createPriceLine({
          price: lvl.price,
          color: lvl.color,
          lineWidth: (lvl.ratio === 0 || lvl.ratio === 1.0 || lvl.ratio === 0.618) ? 1.5 : 1,
          lineStyle: lvl.lineStyle !== undefined ? lvl.lineStyle : 1,
          axisLabelVisible: true,
          title: `${lvl.name} ${lvl.price}`
        });
        this.fibonacciLines.push(line);
      } catch (e) {
        console.warn("Error creating fibonacci price line:", e);
      }
    });
  }

  setTradeMarkers(markers) {
    this.tradeMarkers = markers || [];
    this.updateMarkers();
  }

  clearTradeMarkers() {
    this.tradeMarkers = [];
    this.updateMarkers();
  }


  updateMAAlignmentBadge() {
    const badge = document.getElementById("ma-alignment-badge");
    if (!badge || !this.currentIndicators || !this.currentIndicators.ma) return;
    const ma = this.currentIndicators.ma;
    const m5 = ma.ma5 && ma.ma5.length ? ma.ma5[ma.ma5.length - 1].value : null;
    const m20 = ma.ma20 && ma.ma20.length ? ma.ma20[ma.ma20.length - 1].value : null;
    const m60 = ma.ma60 && ma.ma60.length ? ma.ma60[ma.ma60.length - 1].value : null;

    if (m5 && m20 && m60) {
      if (m5 > m20 && m20 > m60) {
        badge.className = "ma-prominent-tag bull";
        badge.innerHTML = "🔴 多頭排列 (MA5 > MA20 > MA60)";
      } else if (m5 < m20 && m20 < m60) {
        badge.className = "ma-prominent-tag bear";
        badge.innerHTML = "🟢 空頭排列 (MA5 < MA20 < MA60)";
      } else {
        const c = this.currentData && this.currentData.candles && this.currentData.candles.length 
          ? this.currentData.candles[this.currentData.candles.length - 1].close 
          : 0;
        if (c > m20) {
          badge.className = "ma-prominent-tag bull";
          badge.innerHTML = "🔵 站上月線 (股價 > MA20)";
        } else {
          badge.className = "ma-prominent-tag neutral";
          badge.innerHTML = "⚪ 均線糾結整理中";
        }
      }
    }
  }

  clearSubChart() {
    Object.values(this.subSeries).forEach(series => {
      try {
        this.subChart.removeSeries(series);
      } catch (e) {}
    });
    this.subSeries = {};
  }

  setSubIndicator(indicatorName) {
    this.activeSubIndicator = indicatorName;
    if (this.currentData && this.currentIndicators) {
      this.renderSubIndicator(indicatorName);
    }
  }

  renderSubIndicator(indicatorName) {
    this.clearSubChart();
    const { upColor, downColor } = this.getColorTheme();

    if (indicatorName === "volume") {
      const volumeData = (this.currentData.volume || []).map(v => ({
        time: v.time,
        value: v.value,
        color: v.is_up ? (this.isTaiwanColor ? "#ff4d4f" : "#00b96b") : (this.isTaiwanColor ? "#00b96b" : "#ff4d4f")
      }));

      const vSeries = this.subChart.addHistogramSeries({
        priceFormat: { type: "volume" },
        title: "成交量"
      });
      vSeries.setData(volumeData);
      this.subSeries.volume = vSeries;

      // Add VMA5 and VMA20
      const vma = this.currentIndicators.vma || {};
      if (vma.vma5) {
        const vma5Series = this.subChart.addLineSeries({
          color: "#fadb14",
          lineWidth: 1.5,
          title: "VMA5"
        });
        vma5Series.setData(vma.vma5);
        this.subSeries.vma5 = vma5Series;
      }
      if (vma.vma20) {
        const vma20Series = this.subChart.addLineSeries({
          color: "#13c2c2",
          lineWidth: 1.5,
          title: "VMA20"
        });
        vma20Series.setData(vma.vma20);
        this.subSeries.vma20 = vma20Series;
      }

    } else if (indicatorName === "kd") {
      const kd = this.currentIndicators.kd || {};
      const kSeries = this.subChart.addLineSeries({ color: "#1890ff", lineWidth: 1.5, title: "K(9)" });
      const dSeries = this.subChart.addLineSeries({ color: "#faad14", lineWidth: 1.5, title: "D(3)" });

      if (kd.k) kSeries.setData(kd.k);
      if (kd.d) dSeries.setData(kd.d);

      // Reference overbought/oversold levels
      kSeries.createPriceLine({ price: 80, color: "rgba(255, 77, 79, 0.4)", lineStyle: 2, title: "超買 80" });
      kSeries.createPriceLine({ price: 20, color: "rgba(0, 185, 107, 0.4)", lineStyle: 2, title: "超賣 20" });

      this.subSeries.k = kSeries;
      this.subSeries.d = dSeries;

    } else if (indicatorName === "macd") {
      const macd = this.currentIndicators.macd || {};
      const barData = (macd.bar || []).map(b => ({
        time: b.time,
        value: b.value,
        color: b.value >= 0 ? upColor : downColor
      }));

      const barSeries = this.subChart.addHistogramSeries({ title: "OSC" });
      barSeries.setData(barData);

      const difSeries = this.subChart.addLineSeries({ color: "#1890ff", lineWidth: 1.5, title: "DIF" });
      const deaSeries = this.subChart.addLineSeries({ color: "#faad14", lineWidth: 1.5, title: "MACD" });

      if (macd.dif) difSeries.setData(macd.dif);
      if (macd.dea) deaSeries.setData(macd.dea);

      this.subSeries.bar = barSeries;
      this.subSeries.dif = difSeries;
      this.subSeries.dea = deaSeries;

    } else if (indicatorName === "rsi") {
      const rsi = this.currentIndicators.rsi || {};
      const r6 = this.subChart.addLineSeries({ color: "#f759ab", lineWidth: 1.5, title: "RSI(6)" });
      const r12 = this.subChart.addLineSeries({ color: "#13c2c2", lineWidth: 1.5, title: "RSI(12)" });

      if (rsi.rsi6) r6.setData(rsi.rsi6);
      if (rsi.rsi12) r12.setData(rsi.rsi12);

      r6.createPriceLine({ price: 80, color: "rgba(255, 77, 79, 0.4)", lineStyle: 2, title: "超買 80" });
      r6.createPriceLine({ price: 20, color: "rgba(0, 185, 107, 0.4)", lineStyle: 2, title: "超賣 20" });

      this.subSeries.rsi6 = r6;
      this.subSeries.rsi12 = r12;

    } else if (indicatorName === "bias") {
      const bias = this.currentIndicators.bias || {};
      const b20Series = this.subChart.addLineSeries({ color: "#722ed1", lineWidth: 1.5, title: "BIAS(20)" });
      const b60Series = this.subChart.addLineSeries({ color: "#eb2f96", lineWidth: 1.5, title: "BIAS(60)" });
      if (bias.bias20) b20Series.setData(bias.bias20);
      if (bias.bias60) b60Series.setData(bias.bias60);
      b20Series.createPriceLine({ price: 0, color: "rgba(255, 255, 255, 0.2)", lineStyle: 0 });
      this.subSeries.bias20 = b20Series;
      this.subSeries.bias60 = b60Series;

    } else if (indicatorName === "institutional") {
      const instData = this.currentData.institutional || [];
      const totalBarData = instData.map(d => ({
        time: d.time,
        value: d.totalLots,
        color: d.totalLots >= 0 ? upColor : downColor
      }));

      const totalSeries = this.subChart.addHistogramSeries({
        title: "三大法人合計(張)"
      });
      totalSeries.setData(totalBarData);

      const foreignData = instData.map(d => ({ time: d.time, value: d.foreignLots }));
      const trustData = instData.map(d => ({ time: d.time, value: d.trustLots }));

      const foreignSeries = this.subChart.addLineSeries({
        color: "#fa8c16",
        lineWidth: 1.5,
        title: "外資(張)"
      });
      foreignSeries.setData(foreignData);

      const trustSeries = this.subChart.addLineSeries({
        color: "#b37feb",
        lineWidth: 1.8,
        title: "投信(張)"
      });
      trustSeries.setData(trustData);

      totalSeries.createPriceLine({ price: 0, color: "rgba(255, 255, 255, 0.2)", lineStyle: 0 });

      this.subSeries.total = totalSeries;
      this.subSeries.foreign = foreignSeries;
      this.subSeries.trust = trustSeries;
    }
  }

  updateLegend(param) {
    if (!param || !param.time || !param.seriesData || !this.candleSeries) {
      return;
    }

    const candle = param.seriesData.get(this.candleSeries);
    if (!candle) return;

    const o = candle.open || 0;
    const h = candle.high || 0;
    const l = candle.low || 0;
    const c = candle.close || 0;

    // Accurate change against previous bar's close price
    let prevClose = this.candlePrevCloseMap ? this.candlePrevCloseMap.get(param.time) : undefined;
    if (prevClose === undefined || prevClose === null || prevClose <= 0) {
      prevClose = o > 0 ? o : c;
    }

    const chg = c - prevClose;
    const chgPct = prevClose > 0 ? ((chg / prevClose) * 100).toFixed(2) : "0.00";
    const isUp = chg >= 0;
    const colorClass = isUp ? (this.isTaiwanColor ? "up-text" : "down-text") : (this.isTaiwanColor ? "down-text" : "up-text");

    let legendHtml = `
      <div class="legend-item"><span class="legend-label">開:</span><span class="legend-val">${o.toFixed(2)}</span></div>
      <div class="legend-item"><span class="legend-label">高:</span><span class="legend-val">${h.toFixed(2)}</span></div>
      <div class="legend-item"><span class="legend-label">低:</span><span class="legend-val">${l.toFixed(2)}</span></div>
      <div class="legend-item"><span class="legend-label">收:</span><span class="legend-val ${colorClass}">${c.toFixed(2)} (${chg >= 0 ? '+' : ''}${chg.toFixed(2)} / ${chg >= 0 ? '+' : ''}${chgPct}%)</span></div>
    `;

    // Add Institutional values under cursor if active
    if (this.activeSubIndicator === "institutional") {
      const instData = this.currentData ? (this.currentData.institutional || []) : [];
      const pt = instData.find(d => d.time === param.time);
      if (pt) {
        legendHtml += `
          <div class="legend-item"><span class="legend-label">外資:</span><span class="legend-val" style="color:#fa8c16">${pt.foreignLots > 0 ? '+' : ''}${pt.foreignLots}張</span></div>
          <div class="legend-item"><span class="legend-label">投信:</span><span class="legend-val" style="color:#b37feb">${pt.trustLots > 0 ? '+' : ''}${pt.trustLots}張</span></div>
          <div class="legend-item"><span class="legend-label">自營:</span><span class="legend-val" style="color:#36cfc9">${pt.dealerLots > 0 ? '+' : ''}${pt.dealerLots}張</span></div>
        `;
      }
    }

    // Add MA values under cursor
    const maKeys = ["ma5", "ma10", "ma20", "ma60"];
    maKeys.forEach(k => {
      if (this.overlayVisibility[k] && this.maSeries[k]) {
        const maPoint = param.seriesData.get(this.maSeries[k]);
        if (maPoint && maPoint.value !== undefined) {
          legendHtml += `<div class="legend-item"><span class="legend-label">${k.toUpperCase()}:</span><span class="legend-val" style="color:${this.maSeries[k].options().color}">${maPoint.value.toFixed(2)}</span></div>`;
        }
      }
    });

    this.legendContainer.innerHTML = legendHtml;
  }

  updateLegendWithLatest() {
    const candles = this.currentData ? this.currentData.candles : [];
    if (!candles.length) return;
    const latest = candles[candles.length - 1];
    const o = latest.open || 0;
    const h = latest.high || 0;
    const l = latest.low || 0;
    const c = latest.close || 0;

    let prevClose = undefined;
    if (this.currentData && this.currentData.summary && this.currentData.summary.previousClose) {
      prevClose = this.currentData.summary.previousClose;
    } else if (candles.length > 1) {
      prevClose = candles[candles.length - 2].close;
    } else {
      prevClose = o > 0 ? o : c;
    }

    let chg = c - prevClose;
    let chgPct = prevClose > 0 ? ((chg / prevClose) * 100).toFixed(2) : "0.00";
    if (this.currentData && this.currentData.summary && typeof this.currentData.summary.change === "number") {
      chg = this.currentData.summary.change;
      chgPct = Number(this.currentData.summary.changePercent || 0).toFixed(2);
    }

    const isUp = chg >= 0;
    const colorClass = isUp ? (this.isTaiwanColor ? "up-text" : "down-text") : (this.isTaiwanColor ? "down-text" : "up-text");

    let legendHtml = `
      <div class="legend-item"><span class="legend-label">開:</span><span class="legend-val">${o.toFixed(2)}</span></div>
      <div class="legend-item"><span class="legend-label">高:</span><span class="legend-val">${h.toFixed(2)}</span></div>
      <div class="legend-item"><span class="legend-label">低:</span><span class="legend-val">${l.toFixed(2)}</span></div>
      <div class="legend-item"><span class="legend-label">收:</span><span class="legend-val ${colorClass}">${c.toFixed(2)} (${chg >= 0 ? '+' : ''}${chg.toFixed(2)} / ${chg >= 0 ? '+' : ''}${chgPct}%)</span></div>
    `;

    const ma = this.currentIndicators ? this.currentIndicators.ma || {} : {};
    const maConfigs = [
      { key: "ma5", color: "#fadb14", title: "MA5" },
      { key: "ma20", color: "#13c2c2", title: "MA20" },
      { key: "ma60", color: "#722ed1", title: "MA60" }
    ];
    maConfigs.forEach(({ key, color, title }) => {
      if (this.overlayVisibility[key] && ma[key] && ma[key].length > 0) {
        const lastVal = ma[key][ma[key].length - 1].value;
        legendHtml += `<div class="legend-item"><span class="legend-label">${title}:</span><span class="legend-val" style="color:${color}">${lastVal.toFixed(2)}</span></div>`;
      }
    });

    this.legendContainer.innerHTML = legendHtml;
  }

  resizeCharts() {
    if (this.mainChart && this.mainContainer) {
      const w = this.mainContainer.clientWidth;
      const h = this.mainContainer.clientHeight;
      if (w > 0 && h > 0) {
        this.mainChart.applyOptions({ width: w, height: h });
      }
    }
    if (this.subChart && this.subContainer) {
      const w = this.subContainer.clientWidth;
      const h = this.subContainer.clientHeight;
      if (w > 0 && h > 0) {
        this.subChart.applyOptions({ width: w, height: h });
      }
    }
  }

  bindWindowResize() {
    window.addEventListener("resize", () => {
      this.resizeCharts();
    });

    if (window.ResizeObserver) {
      this.resizeObserver = new ResizeObserver(() => {
        this.resizeCharts();
      });
      if (this.mainContainer) this.resizeObserver.observe(this.mainContainer);
      if (this.subContainer) this.resizeObserver.observe(this.subContainer);
    }
  }
}
