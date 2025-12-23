import asyncio
import json
import pandas as pd
from openai import AsyncOpenAI
from src.config import Config

async def analyze_review(client, semaphore, row_data):
    async with semaphore:
        text = f"{row_data.get('Title', '')}. {row_data.get('Content', '')}"[:2000]

        # ======================================================
        # 🧠 双层分类 Prompt (完全保留你的原始内容)
        # ======================================================
        prompt = f"""
        Role: Senior Telecom Analyst for South Africa.
        Task: Analyze the customer review with a 2-level classification system.

        Review: "{text}"

        Classification Rules：以下只是参考，你可以根据实际情况继续修改和完善；
        1. **Level_1_Category**: Choose ONE from [Network, Billing, Customer_Service, Technical_Repair, Sales_Admin, App_Digital, Other].
        2. **Level_2_Issue**: Be specific based on Level 1.
           - If Network: "No Signal/Dead Zone", "Slow Internet/High Latency", "Intermittent Drop", "No Throughput", "Load Shedding Impact".
           - If Billing: "Double Debit", "Price Increase", "Cancellation Failure", "Refund Delay", "OOB Charges".
           - If Service: "Call Center Unreachable", "Rude Agent", "No Feedback", "Chatbot Loop".
           - If Repair: "Technician No-Show", "Router Faulty", "Fibre Break".

        3. **Service_Type**: MBB (Mobile/Sim) or FWA (Wireless home broadband) or Fibre.
        4. **Summary**: A concise 1-sentence summary of the specific incident (e.g. "User charged twice after cancelling contract").

        Output JSON ONLY:
        {{
            "L1_Category": "...",
            "L2_Issue": "...",
            "Service_Type": "...",
            "Sentiment": "Positive/Negative/Neutral",
            "Summary": "..."
        }}
        """

        try:
            response = await client.chat.completions.create(
                model=Config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": "JSON generator. Telecom expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {
                "L1_Category": "Other", "L2_Issue": "Analysis Failed",
                "Service_Type": "Unknown", "Sentiment": "Neutral", "Summary": "Error"
            }

async def run_analysis(df):
    print(f"🧠 [Step 2] 启动双层分类分析...")
    if df.empty: return df

    client = AsyncOpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)
    semaphore = asyncio.Semaphore(10)

    records = df.to_dict('records')
    tasks = [analyze_review(client, semaphore, r) for r in records]
    results = await asyncio.gather(*tasks)

    analysis_df = pd.DataFrame(results)
    final_df = pd.concat([df, analysis_df], axis=1)

    final_df.to_csv(Config.ANALYZED_FILE, index=False, encoding='utf-8-sig')
    print(f"✅ 分析完成！包含 L1/L2 分类与摘要。")
    return final_df
