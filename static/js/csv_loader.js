/**
 * CSV Loader & Importer Module
 * Handles file drag-and-drop, sample loading, parsing, and feeding into chart manager
 */

class CSVLoader {
  constructor(onDataLoaded) {
    this.onDataLoaded = onDataLoaded;
    this.modal = document.getElementById("csv-modal");
    this.dropZone = document.getElementById("csv-drop-zone");
    this.fileInput = document.getElementById("csv-file-input");
    this.loadSampleBtn = document.getElementById("csv-load-sample-btn");
    this.closeBtn = document.getElementById("csv-modal-close");
    this.openBtn = document.getElementById("btn-open-csv-modal");

    this.initEvents();
  }

  initEvents() {
    if (this.openBtn) {
      this.openBtn.addEventListener("click", () => this.openModal());
    }
    if (this.closeBtn) {
      this.closeBtn.addEventListener("click", () => this.closeModal());
    }
    if (this.modal) {
      this.modal.addEventListener("click", (e) => {
        if (e.target === this.modal) this.closeModal();
      });
    }

    // Drag and Drop
    if (this.dropZone) {
      this.dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        this.dropZone.classList.add("drag-over");
      });

      this.dropZone.addEventListener("dragleave", () => {
        this.dropZone.classList.remove("drag-over");
      });

      this.dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        this.dropZone.classList.remove("drag-over");
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
          this.handleFile(e.dataTransfer.files[0]);
        }
      });

      this.dropZone.addEventListener("click", () => {
        if (this.fileInput) this.fileInput.click();
      });
    }

    if (this.fileInput) {
      this.fileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files.length > 0) {
          this.handleFile(e.target.files[0]);
        }
      });
    }

    if (this.loadSampleBtn) {
      this.loadSampleBtn.addEventListener("click", () => this.loadSampleData());
    }
  }

  openModal() {
    if (this.modal) this.modal.classList.add("active");
  }

  closeModal() {
    if (this.modal) this.modal.classList.remove("active");
  }

  async handleFile(file) {
    if (!file.name.endsWith(".csv") && !file.type.includes("csv") && !file.type.includes("text")) {
      if (window.Toast) {
        window.Toast.warning("請上傳副檔名為 .csv 的股票歷史資料檔案");
      }
      return;
    }

    this.showStatus("正在解析 CSV 檔案 (相容 TWSE/民國年/券商格式)...", true);

    try {
      const res = await API.uploadCSV(file);
      this.showStatus(`成功解析 ${res.chartData.candles.length} 筆 K 線數據！`, false);
      if (window.Toast) {
        window.Toast.success(`成功匯入 ${res.chartData.summary.name} (${res.chartData.candles.length} 筆資料)`);
      }
      
      setTimeout(() => {
        this.closeModal();
        if (this.onDataLoaded) {
          this.onDataLoaded(res);
        }
      }, 600);
    } catch (err) {
      this.showStatus(`解析失敗: ${err.message}`, false, true);
      if (window.Toast) {
        window.Toast.error(`CSV 解析失敗: ${err.message}`);
      }
    }
  }

  async loadSampleData() {
    this.showStatus("正在載入範例台股 CSV 數據...", true);
    try {
      const response = await fetch("/static/sample_stock.csv");
      const blob = await response.blob();
      const file = new File([blob], "2330_sample_stock.csv", { type: "text/csv" });
      await this.handleFile(file);
    } catch (err) {
      this.showStatus(`載入範例失敗: ${err.message}`, false, true);
    }
  }

  showStatus(msg, isLoading, isError) {
    const statusEl = document.getElementById("csv-status-msg");
    if (!statusEl) return;
    statusEl.textContent = msg;
    statusEl.style.display = "block";
    statusEl.style.color = isError ? "var(--color-up)" : (isLoading ? "var(--color-accent)" : "var(--color-down)");
  }
}
