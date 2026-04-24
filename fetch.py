import requests
import json
import re
from datetime import datetime, timezone, timedelta

tz = timezone(timedelta(hours=8))
now = datetime.now(tz)
date_short = now.strftime("%Y-%m-%d")
date_display = now.strftime("%m/%d")

stocks = []
seen_ids = set()

def add_stock(stock_id, name, direction, title, reason, source, source_name):
    if stock_id in seen_ids:
        return
    if not re.match(r'^\d{4}$', stock_id):
        return
    seen_ids.add(stock_id)
    stocks.append({
        "id": stock_id,
        "name": name,
        "direction": direction,
        "title": title[:20],
        "reason": reason[:40],
        "source": source,
        "sourceName": source_name,
        "date": date_display,
        "time": now.strftime("%H:%M")
    })

# ── 1. 證交所：當日成交量前20名 ──────────────────────────
def fetch_twse_popular():
    try:
        url = "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX20?response=json"
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        data = r.json()
        rows = data.get("data", [])
        count = 0
        for row in rows[:15]:
            try:
                stock_id = str(row[0]).strip()
                stock_name = str(row[1]).strip()
                chg = str(row[4]).strip()
                direction = "bear" if "-" in chg else "bull"
                add_stock(stock_id, stock_name, direction,
                         "今日成交量排行",
                         f"今日成交量排行，{'上漲' if direction=='bull' else '下跌'}，適合權證追蹤",
                         "twse", "台灣證交所")
                count += 1
            except:
                continue
        print(f"證交所成交量排行: {count} 筆")
    except Exception as e:
        print(f"證交所失敗: {e}")

# ── 2. 證交所：漲幅排行 ──────────────────────────────────
def fetch_twse_gainers():
    try:
        url = "https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d?selectType=UP&response=json"
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        data = r.json()
        rows = data.get("data", [])
        count = 0
        for row in rows[:10]:
            try:
                stock_id = str(row[0]).strip()
                stock_name = str(row[1]).strip()
                if not re.match(r'^\d{4}$', stock_id):
                    continue
                add_stock(stock_id, stock_name, "bull",
                         "今日漲幅排行",
                         f"今日股價上漲，認購權證熱門標的",
                         "twse", "台灣證交所")
                count += 1
            except:
                continue
        print(f"證交所漲幅排行: {count} 筆")
    except Exception as e:
        print(f"證交所漲幅失敗: {e}")

# ── 3. 鉅亨網：漲跌幅排行 ────────────────────────────────
def fetch_cnyes():
    try:
        # 漲幅榜
        for category, direction in [("PERCENT", "bull"), ("PERCENTDOWN", "bear")]:
            url = f"https://ws.api.cnyes.com/ws/api/v1/charting/toplist?market=TWS&category={category}&limit=10"
            r = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.cnyes.com/"
            })
            data = r.json()
            items = data.get("data", {}).get("items", [])
            count = 0
            for item in items[:8]:
                try:
                    code = str(item.get("symbolId", "")).replace(".TW","").strip()
                    name = item.get("nameZF", item.get("name", code))
                    label = "漲幅" if direction == "bull" else "跌幅"
                    add_stock(code, name, direction,
                             f"鉅亨網{label}排行",
                             f"今日{label}排行，{'認購' if direction=='bull' else '認售'}權證標的",
                             "broker", "鉅亨網")
                    count += 1
                except:
                    continue
            print(f"鉅亨網{category}: {count} 筆")
    except Exception as e:
        print(f"鉅亨網失敗: {e}")

# ── 4. 證交所：新增權證標的 ──────────────────────────────
def fetch_twse_new_warrants():
    try:
        url = "https://www.twse.com.tw/rwd/zh/warrant/TWTAUO?response=json"
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            print(f"新增權證狀態碼: {r.status_code}")
            return
        data = r.json()
        rows = data.get("data", [])
        count = 0
        for row in rows[:10]:
            try:
                stock_id = str(row[2]).strip()
                stock_name = str(row[3]).strip()
                cp_type = str(row[4]).strip()
                direction = "bull" if "購" in cp_type else "bear"
                add_stock(stock_id, stock_name, direction,
                         f"新增{cp_type}權證上市",
                         f"券商新增{cp_type}權證，標的 {stock_name}",
                         "twse", "台灣證交所")
                count += 1
            except:
                continue
        print(f"新增權證: {count} 筆")
    except Exception as e:
        print(f"新增權證失敗: {e}")

# ── 執行所有來源 ─────────────────────────────────────────
print(f"開始抓取 {date_short} 權證資料...")
fetch_twse_popular()
fetch_twse_gainers()
fetch_cnyes()
fetch_twse_new_warrants()

print(f"總計 {len(stocks)} 筆不重複標的")

result = {
    "date": date_short,
    "updated": now.strftime("%H:%M"),
    "stocks": stocks[:20]
}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("data.json 已更新！")
