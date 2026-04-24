import requests
import json
import os
import re
from datetime import datetime, timezone, timedelta

tz = timezone(timedelta(hours=8))
now = datetime.now(tz)
date_str = now.strftime("%Y年%m月%d日")
date_short = now.strftime("%Y-%m-%d")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# 抓取財經網站內容
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
            text = re.sub(r'<[^>]+>', ' ', r.text)
            text = re.sub(r'\s+', ' ', text)
            content += text[:3000] + "\n\n"
        except Exception as e:
            print(f"抓取 {url} 失敗: {e}")
    return content

news_content = fetch_news()

prompt = f"""你是台股權證分析助理。今日是{date_str}。

以下是從財經網站抓取的內容，請找出權證相關標的。若內容不足請補充近期台股熱門權證標的。

網站內容：
{news_content[:4000]}

請只回傳 JSON，不要有任何其他文字或markdown符號：
{{
  "date": "{date_short}",
  "updated": "{now.strftime('%H:%M')}",
  "stocks": [
    {{
      "id": "股票代號4碼",
      "name": "公司名稱",
      "direction": "bull或bear",
      "title": "標題摘要20字內",
      "reason": "推薦原因40字內",
      "source": "udn或ctee或broker",
      "sourceName": "來源名稱",
      "date": "報導日期如04/24",
      "time": "時間如08:30"
    }}
  ]
}}"""

headers = {
    "Content-Type": "application/json",
    "x-api-key": ANTHROPIC_API_KEY,
    "anthropic-version": "2023-06-01"
}

payload = {
    "model": "claude-haiku-4-5-20251001",
    "max_tokens": 2000,
    "messages": [{"role": "user", "content": prompt}]
}

try:
    print(f"正在抓取 {date_str} 的權證資料...")
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=payload,
        timeout=60
    )
    print(f"HTTP狀態碼: {response.status_code}")
    response.raise_for_status()

    data = response.json()
    text = data["content"][0]["text"].strip()

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
