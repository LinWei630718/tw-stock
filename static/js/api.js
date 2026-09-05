/**
 * API Client for Taiwan Stock Technical Analysis System
 */

const API = {
  async searchStocks(query) {
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
      return await res.json();
    } catch (err) {
      console.error("Search API Error:", err);
      return { results: [] };
    }
  },

  async getStockData(code, interval = "1d", range = "1y") {
    try {
      const res = await fetch(`/api/stock/${encodeURIComponent(code)}?interval=${interval}&range=${range}`);
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || "無法載入股票資料");
      }
      return await res.json();
    } catch (err) {
      console.error("Stock Data API Error:", err);
      throw err;
    }
  },

  async getIndicators(code, interval = "1d", range = "1y") {
    try {
      const res = await fetch(`/api/indicators/${encodeURIComponent(code)}?interval=${interval}&range=${range}`);
      if (!res.ok) throw new Error("無法計算技術指標");
      return await res.json();
    } catch (err) {
      console.error("Indicators API Error:", err);
      throw err;
    }
  },

  async getDiagnosis(code, interval = "1d", range = "1y") {
    try {
      const res = await fetch(`/api/diagnosis/${encodeURIComponent(code)}?interval=${interval}&range=${range}`);
      if (!res.ok) throw new Error("無法產生技術診斷");
      return await res.json();
    } catch (err) {
      console.error("Diagnosis API Error:", err);
      throw err;
    }
  },

  async getCategories() {
    try {
      const res = await fetch("/api/categories");
      return await res.json();
    } catch (err) {
      console.error("Categories API Error:", err);
      return { categories: {} };
    }
  },

  async runScreener(strategyId) {
    try {
      const res = await fetch(`/api/screener/${encodeURIComponent(strategyId)}`);
      if (!res.ok) throw new Error("選股掃描失敗");
      return await res.json();
    } catch (err) {
      console.error("Screener API Error:", err);
      throw err;
    }
  },

  async runBacktest(code, strategy = "kd_cross", range = "2y", stopLoss = 7.0, takeProfit = 15.0, includeCosts = true) {
    try {
      const res = await fetch(`/api/backtest/${encodeURIComponent(code)}?strategy=${strategy}&range=${range}&stop_loss=${stopLoss}&take_profit=${takeProfit}&include_costs=${includeCosts}`);
      if (!res.ok) throw new Error("回測執行失敗");
      return await res.json();
    } catch (err) {
      console.error("Backtest API Error:", err);
      throw err;
    }
  },

  async getDashboardSummary() {
    try {
      const res = await fetch("/api/dashboard_summary");
      if (!res.ok) throw new Error("無法取得 Dashboard 總覽數據");
      return await res.json();
    } catch (err) {
      console.error("Dashboard API Error:", err);
      throw err;
    }
  },

  async uploadCSV(file) {
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch("/api/upload_csv", {
        method: "POST",
        body: formData
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || "CSV 上傳解析失敗");
      }
      return await res.json();
    } catch (err) {
      console.error("Upload CSV API Error:", err);
      throw err;
    }
  }
};
