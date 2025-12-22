import asyncio
from src.config import Config
from src.scraper import run_scraper
from src.analyzer import run_analysis, generate_summary_text
from src.reporter import clean_data, create_plots, send_email

async def main():
    # 1. 验证配置
    Config.validate()
    
    # 2. 爬取
    df = await run_scraper()
    if df.empty:
        print("⚠️ 无数据，跳过后续步骤")
        return

    # 3. 分析
    df = await run_analysis(df)
    
    # 4. 报告
    df = clean_data(df)
    summary = generate_summary_text(df)
    imgs = create_plots(df)
    send_email(df, summary, imgs)

if __name__ == "__main__":
    asyncio.run(main())
