import requests
import json
import re
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser

tz = timezone(timedelta(hours=8))
now = datetime.now(tz)
date_short = now.strftime("%Y-%m-%d")
date_display = now.strftime("%m/%d")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

stocks = []

# ── 1. 台灣證交所：今日新增權證 ──────────────────────────
def fetch_twse_warrants():
    try:
        url = "https://www.twse.com.tw/rwd/zh/warrant/TWTAUO?response=json"
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json()
        rows = data.get("data", [])
        seen = set()
        for row in rows[:20]:
            try:
                # row: [權證代號, 權證名稱, 標的代號, 標的名稱, 買賣權, ...]
                stock_id = str(row[2]).strip()
                stock_name = str(row[3]).strip()
                cp = str(row[4]).strip()
                if stock_id in seen or not stock_id.isdigit():
                    continue
                seen.add(stock_id)
                direction = "bull" if "購" in cp or "C" in cp.upper() else "bear"
                stocks.append({
                    "id": stock_id,
                    "name": stock_name,
                    "direction": direction,
                    "title": f"今日新增{cp}權證標的",
                    "reason": f"證交所今日新增權證，標的 {stock_name}",
                    "source": "twse",
                    "sourceName": "台灣證交所",
                    "date": date_display,
                    "time": "09:00"
                })
            except:
                continue
        print(f"證交所抓到 {len(seen)} 筆")
    except Exception as e:
        print(f"證交所失敗: {e}")

# ── 2. 鉅亨網權證新聞 ────────────────────────────────────
def fetch_cnyes_warrants():
    try:
        url = "https://news.cnyes.com/api/v3/news/category/tw_warrant?startAt=&endAt=&limit=20"
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json()
        items = data.get("items", {}).get("data", [])
        seen = set()
        for item in items:
            try:
                title = item.get("title", "")
                summary = item.get("summary", "")
                # 從標題找股票代號（4碼數字）
                codes = re.findall(r'\b(\d{4})\b', title + summary)
                for code in codes:
                    if code in seen:
                        continue
                    seen.add(code)
                    # 判斷方向
                    direction = "bear" if any(k in title for k in ["認售","空","賣","跌"]) else "bull"
                    # 取公司名稱（代號後面的中文）
                    name_match = re.search(rf'{code}[\s]*([^\s\d,，、]+)', title)
                    name = name_match.group(1)[:4] if name_match else code
                    stocks.append({
                        "id": code,
                        "name": name,
                        "direction": direction,
                        "title": title[:20],
                        "reason": summary[:40] if summary else title[:40],
                        "source": "broker",
                        "sourceName": "鉅亨網權證",
                        "date": date_display,
                        "time": "08:00"
                    })
            except:
                continue
        print(f"鉅亨網抓到 {len(seen)} 筆")
    except Exception as e:
        print(f"鉅亨網失敗: {e}")

# ── 3. 經濟日報權證版 ────────────────────────────────────
def fetch_udn_warrants():
    try:
        url = "https://money.udn.com/money/story/11074"
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = "utf-8"
        text = re.sub(r'<[^>]+>', ' ', r.text)
        text = re.sub(r'\s+', ' ', text)
        # 找股票代號
        codes = re.findall(r'\((\d{4})\)', text)
        seen = set()
        for code in codes[:10]:
            if code in seen:
                continue
            seen.add(code)
            # 找代號前後的名稱
            name_match = re.search(rf'([^\s\d（(]{2,5})[（(]{code}[）)]', text)
            name = name_match.group(1) if name_match else code
            stocks.append({
                "id": code,
                "name": name,
                "direction": "bull",
                "title": "經濟日報權證版提及",
                "reason": f"經濟日報權證專欄標的 {name}",
                "source": "udn",
                "sourceName": "經濟日報",
                "date": date_display,
                "time": "08:30"
            })
        print(f"經濟日報抓到 {len(seen)} 筆")
    except Exception as e:
        print(f"經濟日報失敗: {e}")

# ── 4. 玩股網權證熱門 ────────────────────────────────────
def fetch_wantgoo_warrants():
    try:
        url = "https://www.wantgoo.com/warrant/news"
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = "utf-8"
        text = re.sub(r'<[^>]+>', ' ', r.text)
        text = re.sub(r'\s+', ' ', text)
        codes = re.findall(r'\b(\d{4})\b', text)
        seen = set()
        for code in codes:
            if code in seen or not (1000 <= int(code) <= 9999):
                continue
            seen.add(code)
            if len(seen) >= 5:
                break
            stocks.append({
                "id": code,
                "name": code,
                "direction": "bull",
                "title": "玩股網權證熱門標的",
                "reason": f"玩股網權證版熱門討論標的",
                "source": "broker",
                "sourceName": "玩股網",
                "date": date_display,
                "time": "09:00"
            })
        print(f"玩股網抓到 {len(seen)} 筆")
    except Exception as e:
        print(f"玩股網失敗: {e}")

# ── 執行所有來源 ─────────────────────────────────────────
print(f"開始抓取 {date_short} 權證資料...")
fetch_twse_warrants()
fetch_cnyes_warrants()
fetch_udn_warrants()
fetch_wantgoo_warrants()

# 去重（同股票代號只保留第一筆）
seen_ids = set()
unique_stocks = []
for s in stocks:
    if s["id"] not in seen_ids:
        seen_ids.add(s["id"])
        unique_stocks.append(s)

print(f"總計 {len(unique_stocks)} 筆不重複標的")

result = {
    "date": date_short,
    "updated": now.strftime("%H:%M"),
    "stocks": unique_stocks[:20]
}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("data.json 已更新！")
