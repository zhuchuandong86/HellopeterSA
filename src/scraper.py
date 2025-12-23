import asyncio
import json
import random
import pandas as pd
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from src.config import Config

async def run_scraper():
    print(f"🕷️ [Step 1] 启动爬虫 | 目标：{Config.TARGET_OPERATORS} | 范围：最近 {Config.DAYS_TO_SCRAPE} 天")
    cutoff_date = datetime.now() - timedelta(days=Config.DAYS_TO_SCRAPE)
    all_data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for company in Config.TARGET_OPERATORS:
            print(f"\n🏢 正在处理: {company}")
            page_num = 1
            stop_company = False

            while not stop_company:
                url = f"https://api.hellopeter.com/consumer/business/{company}/reviews?page={page_num}"
                try:
                    await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    # 获取页面文本内容而不是HTML，因为API返回JSON
                    content = await page.evaluate("() => document.body.innerText")

                    try:
                        reviews = json.loads(content).get('data', [])
                    except:
                        reviews = []

                    if not reviews:
                        print("   -> 无更多数据，停止该运营商。")
                        break

                    valid_count = 0
                    for item in reviews:
                        created_at = item.get('created_at', '')
                        try:
                            review_date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                        except:
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
                            # 尝试构建URL，逻辑取自原代码
                            "Url": f"https://www.hellopeter.com/{company}/reviews/review-{item.get('id')}"
                        })
                        valid_count += 1

                    if valid_count > 0:
                        print(f"   第 {page_num} 页: 抓取 {valid_count} 条")
                        page_num += 1
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                    else:
                        stop_company = True

                except Exception as e:
                    print(f"   ❌ 错误: {e}")
                    break

        await browser.close()

    if all_data:
        df = pd.DataFrame(all_data)
        # 保存中间文件，方便调试，也符合你原有的流程
        df.to_csv(Config.RAW_FILE, index=False, encoding='utf-8-sig')
        print(f"\n✅ [Step 1 完成] 数据已保存至 {Config.RAW_FILE} (共 {len(df)} 条)")
        return df
    else:
        print("\n⚠️ [Step 1 警告] 未抓取到任何数据。")
        return pd.DataFrame()
