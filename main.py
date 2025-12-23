import asyncio
import seaborn as sns
from src.scraper import run_scraper
from src.analyzer import run_analysis
from src.reporter import clean_data, generate_deep_insight_summary, plot_trend, plot_category, plot_deep_dive, generate_customer_voice, generate_cluster_table, send_report

async def main():
    print("🚀 任务开始...")
    
    # 1. 爬取
    df = await run_scraper()
    if df.empty:
        print("⚠️ 无数据，结束任务")
        return

    # 2. 分析
    df = await run_analysis(df)
    
    # 3. 报告
    print("📊 开始生成报告...")
    df = clean_data(df)
    
    # 设置绘图风格
    sns.set_theme(style="whitegrid", font="sans-serif")
    
    # 生成各部分内容
    summary = generate_deep_insight_summary(df)
    b_trend = plot_trend(df)
    b_cat = plot_category(df)
    b_deep = plot_deep_dive(df)
    voice_html = generate_customer_voice(df)
    monitor_html = generate_cluster_table(df)
    
    # 发送
    send_report(df, summary, b_trend, b_cat, b_deep, voice_html, monitor_html)
    print("🎉 任务全部完成")

if __name__ == "__main__":
    asyncio.run(main())
