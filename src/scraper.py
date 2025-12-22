import asyncio
import json
import random
import pandas as pd
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from src.config import Config

async def run_scraper():
    print(f"🕷️ [Step 1] 启动爬虫 | 范围：最近 {Config.DAYS_TO_SCRAPE} 天")
    cutoff_date = datetime.now() - timedelta(days=Config.DAYS_TO_SCRAPE)
    all_data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for company in Config.TARGET_OPERATORS:
            print(f"   🏢 处理: {company}")
            page_num = 1
            stop_company = False

            while not stop_company:
                url = f"https://api.hellopeter.com/consumer/business/{company}/reviews?page={page_num}"
                try:
                    await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    content = await page.evaluate("() => document.body.innerText")
                    
                    try:
                        reviews = json.loads(content).get('data', [])
                    except json.JSONDecodeError:
                        reviews = []

                    if not reviews:
                        break

                    valid_count_in_page = 0
                    for item in reviews:
                        created_at = item.get('created_at', '')
                        try:
                            review_date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            review_date = datetime.now()

                        if review_date < cutoff_date:
                            stop_company = True
                            continue

                        all_data.append({
                            "Operator": company,
                            "Date": review_date,
                            "Title": item.get('review_title', ''),
                            "Content": item.get('review_content', ''),
                            "Raw_Rating": item.get('review_rating', 0),
                            "Url": f"https://www.hellopeter.com/{company}/reviews/review-{item.get('id')}" # 尝试构建URL
                        })
                        valid_count_in_page += 1

                    if valid_count_in_page > 0:
                        page_num += 1
                        await asyncio.sleep(random.uniform(0.5, 1.0))
                    else:
                        stop_company = True

                except Exception as e:
                    print(f"   ❌ 错误: {e}")
                    stop_company = True

        await browser.close()

    df = pd.DataFrame(all_data)
    print(f"✅ 抓取完成，共 {len(df)} 条数据")
    return df
