import requests
import json
import os
from datetime import datetime, timezone, timedelta

# 台灣時間
tz = timezone(timedelta(hours=8))
now = datetime.now(tz)
date_str = now.strftime("%Y年%m月%d日")
date_short = now.strftime("%Y-%m-%d")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

prompt = f"""你是台股權證分析助理。請搜尋今日（{date_str}）台灣各大財經媒體的權證相關報導，從中找出被提及的權證標的股票。

請回傳 JSON 格式，結構如下（只回傳 JSON，不要有其他文字、不要有markdown符號）：
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
source: udn=經濟日報, ctee=工商時報, broker=券商
至少找5筆，最多15筆，依日期由新到舊排序。"""

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

payload = {
    "contents": [{"parts": [{"text": prompt}]}],
    "tools": [{"google_search": {}}],
    "generationConfig": {
        "temperature": 0.3,
        "maxOutputTokens": 2000
    }
}

try:
    print(f"正在抓取 {date_str} 的權證資料...")
    response = requests.post(url, json=payload, timeout=60)
    response.raise_for_status()

    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]

    # 清除 markdown 符號
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
