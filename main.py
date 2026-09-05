"""
Taiwan Stock Technical Analysis System - Server Launcher
"""

import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add backend directory to python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

import threading
import time
import webbrowser
import urllib.request

import uvicorn

def open_browser_when_ready(host="127.0.0.1", port=8000):
    """Wait for FastAPI/uvicorn server to be fully responsive before opening browser"""
    url = f"http://{host}:{port}"
    for _ in range(30):
        time.sleep(0.3)
        try:
            with urllib.request.urlopen(url, timeout=0.5) as response:
                if response.status == 200:
                    print(f"🚀 伺服器已就緒，正在自動開啟瀏覽器: {url}")
                    webbrowser.open(url)
                    return
        except Exception:
            pass
    # Fallback open if poll timed out but process is alive
    webbrowser.open(url)

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0" if os.environ.get("PROD") == "1" else "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))

    print("=" * 60)
    print("📈 台灣股票技術分析系統 (TW Stock Pro) 啟動中...")
    print(f"👉 伺服器位址: http://{host}:{port}")
    print("👉 若要停止伺服器，請在此視窗按下 Ctrl + C")
    print("=" * 60)

    # In server/container environments or when NO_BROWSER is set, do not pop up browser
    if os.environ.get("NO_BROWSER") != "1" and host == "127.0.0.1":
        browser_thread = threading.Thread(target=open_browser_when_ready, args=(host, port), daemon=True)
        browser_thread.start()

    uvicorn.run("backend.app:app", host=host, port=port, reload=False)
