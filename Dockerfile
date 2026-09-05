# 使用輕量級 Python 3.11 映像檔
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 設定環境變數：關閉 Python 輸出緩衝、指定無桌面環境
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NO_BROWSER=1 \
    HOST=0.0.0.0 \
    PORT=8000

# 複製依賴清單並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案程式碼與靜態前端資源
COPY . .

# 對外開放 8000 連接埠
EXPOSE 8000

# 啟動應用程式
CMD ["python", "main.py"]
