import requests
import json
import os
import re
from datetime import datetime, timezone, timedelta

tz = timezone(timedelta(hours=8))
now = datetime.now(tz)
date_str = now.strftime("%Y年%m月%d日")
date_short = now.strftime("%Y-%m-%d")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 直接抓取經濟日報權證新聞
def fetch_news():
    urls = [
        "https://money.udn.com/money/story/11074",
        "https://www.ctee.com.tw/wealth/stock",
    ]
    content = ""
    headers = {"User-Agent": "Mozilla/5.0"}
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            r.encoding = "utf-8"
            text = r.text
            # 簡單清理 HTML
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text)
            content += text[:3000] + "\n\n"
        except Exception as e:
            print(f"抓取 {url} 失敗: {e}")
    return content

news_content = fetch_news()

prompt = f"""你是台股權證分析助理。以下是今日（{date_str}）從財經網站抓取的內容，請從中找出權證相關標的股票。
如果內容不足，請根據你對台股的知識，補充最近常被討論的權證熱門標的。

網站內容：
{news_content[:4000]}

請回傳 JSON 格式（只回傳 JSON，不要有其他文字、不要有markdown符號）：
{{
  "date": "{date_short}",
  "updated": "{now.strftime('%H:%M')}",
  "stocks": [
    {{
      "id": "股票代號4碼",
      "name": "公司名稱",
      "direction": "bull或bear",
      "title": "標題或摘要20字內",
      "reason": "推薦原因40字內",
      "source": "udn或ctee或broker",
      "sourceName": "來源名稱",
      "date": "報導日期如04/24",
      "time": "時間如08:30"
    }}
  ]
}}

direction: bull=看多/認購, bear=看空/認售
至少5筆，最多15筆。"""

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"

payload = {
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {
        "temperature": 0.3,
        "maxOutputTokens": 2000
    }
}

try:
    print(f"正在抓取 {date_str} 的權證資料...")
    response = requests.post(url, json=payload, timeout=60)
    print(f"HTTP狀態碼: {response.status_code}")
    response.raise_for_status()

    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]

    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    parsed = json.loads(text)

    if "stocks" not in parsed:
        raise ValueError("回傳格式錯誤")

    print(f"成功取得 {len(parsed['stocks'])} 筆標的")

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)

    print("data.json 已更新！")

except Exception as e:
    print(f"發生錯誤: {e}")
    error_data = {
        "date": date_short,
        "updated": now.strftime("%H:%M"),
        "error": str(e),
        "stocks": []
    }
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(error_data, f, ensure_ascii=False, indent=2)
    raise
