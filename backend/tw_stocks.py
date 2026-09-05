"""
Taiwan Stock Master Database & Lookup Utility
Supports listed (TWSE, .TW) and OTC (TPEx, .TWO) stocks, with Chinese names,
industries, and popular watchlist categories.
"""

from typing import List, Dict, Any
import requests
import json
import os

# Top popular Taiwan stocks pre-indexed for instant offline availability
POPULAR_CATEGORIES = {
    "權值領頭": [
        {"code": "2330", "symbol": "2330.TW", "name": "台積電", "industry": "半導體業", "market": "TWSE"},
        {"code": "2317", "symbol": "2317.TW", "name": "鴻海", "industry": "其他電子業", "market": "TWSE"},
        {"code": "2454", "symbol": "2454.TW", "name": "聯發科", "industry": "半導體業", "market": "TWSE"},
        {"code": "2308", "symbol": "2308.TW", "name": "台達電", "industry": "電子零組件業", "market": "TWSE"},
        {"code": "2382", "symbol": "2382.TW", "name": "廣達", "industry": "電腦及週邊設備業", "market": "TWSE"},
        {"code": "2881", "symbol": "2881.TW", "name": "富邦金", "industry": "金融保險業", "market": "TWSE"},
        {"code": "2882", "symbol": "2882.TW", "name": "國泰金", "industry": "金融保險業", "market": "TWSE"},
        {"code": "2412", "symbol": "2412.TW", "name": "中華電", "industry": "通信網路業", "market": "TWSE"},
        {"code": "2303", "symbol": "2303.TW", "name": "聯電", "industry": "半導體業", "market": "TWSE"},
        {"code": "3711", "symbol": "3711.TW", "name": "日月光投控", "industry": "半導體業", "market": "TWSE"},
    ],
    "AI供應鏈": [
        {"code": "2382", "symbol": "2382.TW", "name": "廣達", "industry": "AI伺服器", "market": "TWSE"},
        {"code": "3231", "symbol": "3231.TW", "name": "緯創", "industry": "AI伺服器", "market": "TWSE"},
        {"code": "2376", "symbol": "2376.TW", "name": "技嘉", "industry": "AI伺服器", "market": "TWSE"},
        {"code": "3017", "symbol": "3017.TW", "name": "奇鋐", "industry": "AI散熱", "market": "TWSE"},
        {"code": "3324", "symbol": "3324.TWO", "name": "雙鴻", "industry": "AI散熱", "market": "TPEx"},
        {"code": "6669", "symbol": "6669.TW", "name": "緯穎", "industry": "AI伺服器", "market": "TWSE"},
        {"code": "2356", "symbol": "2356.TW", "name": "英業達", "industry": "電腦週邊", "market": "TWSE"},
        {"code": "3653", "symbol": "3653.TW", "name": "健策", "industry": "散熱導線架", "market": "TWSE"},
        {"code": "2059", "symbol": "2059.TW", "name": "川湖", "industry": "伺服器導軌", "market": "TWSE"},
        {"code": "3443", "symbol": "3443.TW", "name": "創意", "industry": "ASIC設計", "market": "TWSE"},
        {"code": "3661", "symbol": "3661.TW", "name": "世芯-KY", "industry": "ASIC設計", "market": "TWSE"},
    ],
    "熱門ETF": [
        {"code": "0050", "symbol": "0050.TW", "name": "元大台灣50", "industry": "指數股票型基金", "market": "TWSE"},
        {"code": "0056", "symbol": "0056.TW", "name": "元大高股息", "industry": "指數股票型基金", "market": "TWSE"},
        {"code": "00878", "symbol": "00878.TW", "name": "國泰永續高股息", "industry": "指數股票型基金", "market": "TWSE"},
        {"code": "00919", "symbol": "00919.TW", "name": "群益台灣精選高息", "industry": "指數股票型基金", "market": "TWSE"},
        {"code": "00929", "symbol": "00929.TW", "name": "復華台灣科技優息", "industry": "指數股票型基金", "market": "TWSE"},
        {"code": "00940", "symbol": "00940.TW", "name": "元大台灣價值高息", "industry": "指數股票型基金", "market": "TWSE"},
        {"code": "006208", "symbol": "006208.TW", "name": "富邦台50", "industry": "指數股票型基金", "market": "TWSE"},
        {"code": "00713", "symbol": "00713.TW", "name": "元大台灣高息低波", "industry": "指數股票型基金", "market": "TWSE"},
    ],
    "航運航太": [
        {"code": "2603", "symbol": "2603.TW", "name": "長榮", "industry": "航運業", "market": "TWSE"},
        {"code": "2609", "symbol": "2609.TW", "name": "陽明", "industry": "航運業", "market": "TWSE"},
        {"code": "2615", "symbol": "2615.TW", "name": "萬海", "industry": "航運業", "market": "TWSE"},
        {"code": "2618", "symbol": "2618.TW", "name": "長榮航", "industry": "航空業", "market": "TWSE"},
        {"code": "2610", "symbol": "2610.TW", "name": "華航", "industry": "航空業", "market": "TWSE"},
        {"code": "2637", "symbol": "2637.TW", "name": "慧洋-KY", "industry": "散裝航運", "market": "TWSE"},
        {"code": "2605", "symbol": "2605.TW", "name": "新興", "industry": "散裝航運", "market": "TWSE"},
    ],
    "高人氣OTC": [
        {"code": "8069", "symbol": "8069.TWO", "name": "元太", "industry": "電子零組件業", "market": "TPEx"},
        {"code": "6547", "symbol": "6547.TWO", "name": "高端疫苗", "industry": "生技醫療業", "market": "TPEx"},
        {"code": "3293", "symbol": "3293.TWO", "name": "鈊象", "industry": "資訊服務業", "market": "TPEx"},
        {"code": "6488", "symbol": "6488.TWO", "name": "環球晶", "industry": "半導體業", "market": "TPEx"},
        {"code": "5483", "symbol": "5483.TWO", "name": "中美晶", "industry": "半導體業", "market": "TPEx"},
        {"code": "3131", "symbol": "3131.TWO", "name": "弘塑", "industry": "半導體設備", "market": "TPEx"},
        {"code": "3529", "symbol": "3529.TWO", "name": "力旺", "industry": "半導體IP", "market": "TPEx"},
    ]
}

# In-memory database of all known TW stocks
_STOCKS_CACHE: Dict[str, Dict[str, Any]] = {}

def initialize_stock_database():
    """Initializes the database from popular categories and preloaded definitions."""
    global _STOCKS_CACHE
    if _STOCKS_CACHE:
        return

    # Load from preloaded categories
    for cat_name, stocks in POPULAR_CATEGORIES.items():
        for s in stocks:
            _STOCKS_CACHE[s["code"]] = s

    # Add more key TWSE & TPEx common stocks
    more_stocks = [
        {"code": "2357", "symbol": "2357.TW", "name": "華碩", "industry": "電腦週邊", "market": "TWSE"},
        {"code": "2301", "symbol": "2301.TW", "name": "光寶科", "industry": "電子零組件", "market": "TWSE"},
        {"code": "2886", "symbol": "2886.TW", "name": "兆豐金", "industry": "金融保險", "market": "TWSE"},
        {"code": "2891", "symbol": "2891.TW", "name": "中信金", "industry": "金融保險", "market": "TWSE"},
        {"code": "2884", "symbol": "2884.TW", "name": "玉山金", "industry": "金融保險", "market": "TWSE"},
        {"code": "2880", "symbol": "2880.TW", "name": "華南金", "industry": "金融保險", "market": "TWSE"},
        {"code": "2892", "symbol": "2892.TW", "name": "第一金", "industry": "金融保險", "market": "TWSE"},
        {"code": "5880", "symbol": "5880.TW", "name": "合庫金", "industry": "金融保險", "market": "TWSE"},
        {"code": "2002", "symbol": "2002.TW", "name": "中鋼", "industry": "鋼鐵工業", "market": "TWSE"},
        {"code": "1301", "symbol": "1301.TW", "name": "台塑", "industry": "塑膠工業", "market": "TWSE"},
        {"code": "1303", "symbol": "1303.TW", "name": "南亞", "industry": "塑膠工業", "market": "TWSE"},
        {"code": "1326", "symbol": "1326.TW", "name": "台化", "industry": "塑膠工業", "market": "TWSE"},
        {"code": "6505", "symbol": "6505.TW", "name": "台塑化", "industry": "油電燃氣", "market": "TWSE"},
        {"code": "2327", "symbol": "2327.TW", "name": "國巨", "industry": "被動元件", "market": "TWSE"},
        {"code": "3008", "symbol": "3008.TW", "name": "大立光", "industry": "光電業", "market": "TWSE"},
        {"code": "2379", "symbol": "2379.TW", "name": "瑞昱", "industry": "IC設計", "market": "TWSE"},
        {"code": "3034", "symbol": "3034.TW", "name": "聯詠", "industry": "IC設計", "market": "TWSE"},
        {"code": "2345", "symbol": "2345.TW", "name": "智邦", "industry": "網通業", "market": "TWSE"},
        {"code": "3037", "symbol": "3037.TW", "name": "欣興", "industry": "載板", "market": "TWSE"},
        {"code": "8046", "symbol": "8046.TW", "name": "南電", "industry": "載板", "market": "TWSE"},
        {"code": "3189", "symbol": "3189.TW", "name": "景碩", "industry": "載板", "market": "TWSE"},
        {"code": "1519", "symbol": "1519.TW", "name": "華城", "industry": "重電設備", "market": "TWSE"},
        {"code": "1513", "symbol": "1513.TW", "name": "中興電", "industry": "重電設備", "market": "TWSE"},
        {"code": "1504", "symbol": "1504.TW", "name": "東元", "industry": "電機機械", "market": "TWSE"},
        {"code": "1503", "symbol": "1503.TW", "name": "士電", "industry": "重電設備", "market": "TWSE"},
        {"code": "1609", "symbol": "1609.TW", "name": "大亞", "industry": "電線電纜", "market": "TWSE"},
        {"code": "2395", "symbol": "2395.TW", "name": "研華", "industry": "工業電腦", "market": "TWSE"},
        {"code": "2353", "symbol": "2353.TW", "name": "宏碁", "industry": "電腦週邊", "market": "TWSE"},
        {"code": "2324", "symbol": "2324.TW", "name": "仁寶", "industry": "電腦週邊", "market": "TWSE"},
        {"code": "2377", "symbol": "2377.TW", "name": "微星", "industry": "電腦週邊", "market": "TWSE"},
        {"code": "4938", "symbol": "4938.TW", "name": "和碩", "industry": "代工組裝", "market": "TWSE"},
        {"code": "6770", "symbol": "6770.TW", "name": "力積電", "industry": "晶圓代工", "market": "TWSE"},
        {"code": "2344", "symbol": "2344.TW", "name": "華邦電", "industry": "記憶體", "market": "TWSE"},
        {"code": "2408", "symbol": "2408.TW", "name": "南亞科", "industry": "記憶體", "market": "TWSE"},
        {"code": "3045", "symbol": "3045.TW", "name": "台灣大", "industry": "通信網路", "market": "TWSE"},
        {"code": "4904", "symbol": "4904.TW", "name": "遠傳", "industry": "通信網路", "market": "TWSE"},
        {"code": "9910", "symbol": "9910.TW", "name": "豐泰", "industry": "製鞋", "market": "TWSE"},
        {"code": "9904", "symbol": "9904.TW", "name": "寶成", "industry": "製鞋", "market": "TWSE"},
        {"code": "1101", "symbol": "1101.TW", "name": "台泥", "industry": "水泥工業", "market": "TWSE"},
        {"code": "1102", "symbol": "1102.TW", "name": "亞泥", "industry": "水泥工業", "market": "TWSE"},
        {"code": "1216", "symbol": "1216.TW", "name": "統一", "industry": "食品工業", "market": "TWSE"},
        {"code": "2912", "symbol": "2912.TW", "name": "統一超", "industry": "貿易百貨", "market": "TWSE"},
        {"code": "2207", "symbol": "2207.TW", "name": "和泰車", "industry": "汽車工業", "market": "TWSE"},
        {"code": "2201", "symbol": "2201.TW", "name": "裕隆", "industry": "汽車工業", "market": "TWSE"},
        {"code": "2614", "symbol": "2614.TW", "name": "東森", "industry": "航運業", "market": "TWSE"},
        {"code": "5347", "symbol": "5347.TWO", "name": "世界", "industry": "晶圓代工", "market": "TPEx"},
        {"code": "6274", "symbol": "6274.TWO", "name": "台燿", "industry": "銅箔基板", "market": "TPEx"},
        {"code": "8299", "symbol": "8299.TWO", "name": "群聯", "industry": "IC設計", "market": "TPEx"},
        {"code": "4966", "symbol": "4966.TWO", "name": "譜瑞-KY", "industry": "IC設計", "market": "TPEx"},
        {"code": "6121", "symbol": "6121.TWO", "name": "新普", "industry": "電池模組", "market": "TPEx"}
    ]
    for s in more_stocks:
        _STOCKS_CACHE[s["code"]] = s

    # Load and register all official TWSE/TPEx ETFs dynamically
    load_official_etf_catalog()

def load_official_etf_catalog():
    """
    Dynamically fetches all TWSE/TPEx ETF names from official MIS all_etf.txt
    and caches them with correct Chinese names and market symbols.
    """
    global _STOCKS_CACHE
    try:
        import urllib.request
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        url = "https://mis.twse.com.tw/stock/data/all_etf.txt"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        for g in data.get("a1", []):
            for m in g.get("msgArray", []):
                code = str(m.get("a", "")).strip()
                name = str(m.get("b", "")).strip()
                if not code or not name:
                    continue

                # Clean up overly verbose fund disclosures if present
                clean_name = name.split("(")[0].split("（")[0].strip()
                market = "TPEx" if code.endswith("B") else "TWSE"
                suffix = ".TWO" if market == "TPEx" else ".TW"

                # Store into stock cache if not already existing or overwrite generic placeholder
                if code not in _STOCKS_CACHE or _STOCKS_CACHE[code]["name"].startswith("台股"):
                    _STOCKS_CACHE[code] = {
                        "code": code,
                        "symbol": f"{code}{suffix}",
                        "name": clean_name,
                        "industry": "指數股票型基金",
                        "market": market
                    }

        # User alias calibration (e.g. 00405A -> 主動富邦台灣龍耀, 00403A -> 主動統一升級50)
        active_etf_map = {
            "00403A": {"name": "主動統一升級50", "aliases": ["統一升級50"]},
            "00405A": {"name": "主動富邦台灣龍耀", "aliases": ["富邦台灣龍耀"]},
            "00406A": {"name": "主動中信台灣收益", "aliases": ["中信台灣收益"]},
            "00407A": {"name": "主動凱基台灣", "aliases": ["凱基台灣"]},
            "00408A": {"name": "主動第一金優股息", "aliases": ["第一金優股息"]},
            "00409A": {"name": "主動復華全球50", "aliases": ["復華全球50"]},
            "00400A": {"name": "主動國泰動能高息", "aliases": ["國泰動能高息"]},
            "00401A": {"name": "主動摩根台灣鑫收", "aliases": ["摩根台灣鑫收"]},
            "00402A": {"name": "主動安聯美國科技", "aliases": ["安聯美國科技"]},
            "00404A": {"name": "主動聯博動能50", "aliases": ["聯博動能50"]},
            "00411A": {"name": "主動統一前沿科技", "aliases": ["統一前沿科技"]}
        }
        for c, info in active_etf_map.items():
            n = info["name"]
            aliases = info["aliases"]
            if c in _STOCKS_CACHE:
                _STOCKS_CACHE[c]["name"] = n
                _STOCKS_CACHE[c]["aliases"] = aliases
            else:
                _STOCKS_CACHE[c] = {
                    "code": c,
                    "symbol": f"{c}.TW",
                    "name": n,
                    "aliases": aliases,
                    "industry": "主動式ETF",
                    "market": "TWSE"
                }

    except Exception as e:
        # Fallback manual mappings for active ETFs
        fallback_active_etfs = [
            ("00403A", "主動統一升級50", ["統一升級50"]),
            ("00405A", "主動富邦台灣龍耀", ["富邦台灣龍耀"]),
            ("00406A", "主動中信台灣收益", ["中信台灣收益"]),
            ("00407A", "主動凱基台灣", ["凱基台灣"]),
            ("00408A", "主動第一金優股息", ["第一金優股息"]),
            ("00409A", "主動復華全球50", ["復華全球50"]),
            ("00400A", "主動國泰動能高息", ["國泰動能高息"]),
            ("00401A", "主動摩根台灣鑫收", ["摩根台灣鑫收"]),
            ("00402A", "主動安聯美國科技", ["安聯美國科技"]),
            ("00404A", "主動聯博動能50", ["聯博動能50"]),
            ("00411A", "主動統一前沿科技", ["統一前沿科技"])
        ]
        for c, n, aliases in fallback_active_etfs:
            _STOCKS_CACHE[c] = {
                "code": c,
                "symbol": f"{c}.TW",
                "name": n,
                "aliases": aliases,
                "industry": "主動式ETF",
                "market": "TWSE"
            }

def search_stocks(query: str, limit: int = 15) -> List[Dict[str, Any]]:
    """
    Search stocks by code or Chinese name.
    """
    initialize_stock_database()
    query = query.strip().upper()
    if not query:
        # Return top 15 defaults
        return list(_STOCKS_CACHE.values())[:limit]

    # Normalize by stripping .TW or .TWO
    import re
    clean_query = re.sub(r'\.(TWO|TW)$', '', query, flags=re.IGNORECASE).strip()

    results = []
    # 1. Exact code match (with or without .TW / .TWO)
    if clean_query in _STOCKS_CACHE:
        results.append(_STOCKS_CACHE[clean_query])
    elif query in _STOCKS_CACHE:
        results.append(_STOCKS_CACHE[query])

    # 2. Code prefix match or Name/Alias contains match
    for code, item in _STOCKS_CACHE.items():
        if item in results:
            continue
        matches_name = clean_query in item["name"].upper()
        matches_alias = any(clean_query in str(a).upper() for a in item.get("aliases", []))
        if code.startswith(clean_query) or matches_name or matches_alias:
            results.append(item)
            if len(results) >= limit:
                break

    # 3. If still space, check if query looks like a code not in cache (e.g. user typed 3008, 00405A or 2330.TW)
    if not results and (clean_query.isdigit() or (clean_query.startswith("00") and len(clean_query) >= 4)):
        pure_code = clean_query
        # Guess market: default .TW
        market = "TPEx" if (query.endswith(".TWO") or pure_code.endswith("B")) else "TWSE"
        suffix = ".TWO" if market == "TPEx" else ".TW"
        is_etf_guess = pure_code.startswith("00")
        results.append({
            "code": pure_code,
            "symbol": f"{pure_code}{suffix}",
            "name": f"ETF {pure_code}" if is_etf_guess else f"台股 {pure_code}",
            "industry": "指數股票型基金" if is_etf_guess else "一般類股",
            "market": market
        })

    return results

def get_stock_info(symbol_or_code: str) -> Dict[str, Any]:
    """
    Get stock metadata by code or symbol.
    """
    initialize_stock_database()
    import re
    code = re.sub(r'\.(TWO|TW)$', '', str(symbol_or_code).strip(), flags=re.IGNORECASE).strip()
    if code in _STOCKS_CACHE:
        return _STOCKS_CACHE[code]
    
    # Check symbol
    for item in _STOCKS_CACHE.values():
        if item["symbol"].upper() == symbol_or_code.upper():
            return item
            
    # Default fallback
    market = "TPEx" if (symbol_or_code.upper().endswith(".TWO") or code.endswith("B")) else "TWSE"
    suffix = ".TWO" if market == "TPEx" else ".TW"
    is_etf_guess = code.startswith("00")
    fallback_item = {
        "code": code,
        "symbol": f"{code}{suffix}",
        "name": f"ETF {code}" if is_etf_guess else f"台股 {code}",
        "industry": "指數股票型基金" if is_etf_guess else "台股標的",
        "market": market
    }
    _STOCKS_CACHE[code] = fallback_item
    return fallback_item

def get_watchlist_categories() -> Dict[str, List[Dict[str, Any]]]:
    """Returns the popular category presets."""
    initialize_stock_database()
    return POPULAR_CATEGORIES

def is_etf(symbol_or_code: str) -> bool:
    """Determine if a stock code or symbol is a Taiwan ETF."""
    info = get_stock_info(symbol_or_code)
    code = info.get("code", str(symbol_or_code).split(".")[0]).strip()
    industry = info.get("industry", "")
    if code.startswith("00"):
        return True
    if "ETF" in industry.upper() or "指數股票型" in industry:
        return True
    return False
