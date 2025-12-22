import asyncio
import json
import pandas as pd
from openai import AsyncOpenAI
from src.config import Config

async def analyze_single_review(client, semaphore, row_data):
    async with semaphore:
        text = f"{row_data.get('Title', '')}. {row_data.get('Content', '')}"[:1500]
        
        prompt = f"""
        Role: Telecom Analyst. Analyze this review.
        Review: "{text}"
        
        Output JSON ONLY:
        {{
            "L1_Category": "Network/Billing/Customer_Service/Technical_Repair/Sales/Other",
            "L2_Issue": "Specific root cause (e.g. No Signal, Double Debit)",
            "Service_Type": "Fibre/FWA/MBB",
            "Sentiment": "Positive/Negative",
            "Summary": "1 sentence summary"
        }}
        """

        try:
            response = await client.chat.completions.create(
                model=Config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": "JSON generator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            return {
                "L1_Category": "Other", "L2_Issue": "Error",
                "Service_Type": "Unknown", "Sentiment": "Neutral", "Summary": "Analysis Failed"
            }

async def run_analysis(df):
    if df.empty:
        return df
    
    print("🧠 [Step 2] 开始 AI 分析...")
    client = AsyncOpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)
    semaphore = asyncio.Semaphore(10) # 控制并发

    tasks = [analyze_single_review(client, semaphore, r) for r in df.to_dict('records')]
    results = await asyncio.gather(*tasks)

    analysis_df = pd.DataFrame(results)
    final_df = pd.concat([df, analysis_df], axis=1)
    return final_df

def generate_summary_text(df):
    # 同步调用生成总摘要
    from openai import OpenAI
    client = OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)
    
    stats = df['Operator'].value_counts().to_string()
    issues = df[df['Sentiment']=='Negative']['L2_Issue'].value_counts().head(5).to_string()
    
    prompt = f"""
    你是首席分析师。基于数据写一段简短的中文周报摘要（HTML格式）。
    数据：\n{stats}\n主要问题：\n{issues}
    要求：包含市场总评、主要痛点、改进建议。
    """
    try:
        resp = client.chat.completions.create(
            model=Config.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return resp.choices[0].message.content
    except:
        return "无法生成摘要"
