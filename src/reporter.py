import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import smtplib
from datetime import datetime
from openai import OpenAI
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from src.config import Config

# 设置 Backend 防止无头模式报错
plt.switch_backend('Agg')

def clean_data(df):
    df.columns = df.columns.str.lower().str.strip()
    rename_map = {
        'l1_category': 'L1_Category', 'category': 'L1_Category',
        'l2_issue': 'L2_Issue', 'root_cause': 'L2_Issue',
        'operator': 'Operator', 'date': 'Date', 'sentiment': 'Sentiment',
        'service_type': 'Service_Type', 'service': 'Service_Type',
        'location': 'Location', 'content': 'Content', 'url': 'Url', 'link': 'Url'
    }
    df.rename(columns=rename_map, inplace=True)

    for col in ['L1_Category', 'L2_Issue', 'Service_Type', 'Sentiment', 'Location', 'Content']:
        if col not in df.columns: df[col] = 'Unknown'
    if 'Url' not in df.columns: df['Url'] = ''
    if 'Urgency' not in df.columns: df['Urgency'] = 0

    op_clean_map = {
        'rain-internet-service-provider': 'Rain', 'rain 5g': 'Rain',
        'mtn-service-provider': 'MTN', 'vodacom-provider': 'Vodacom',
        'telkom-sa': 'Telkom'
    }
    df['Operator'] = df['Operator'].astype(str).str.strip().replace(op_clean_map)
    df['Operator'] = df['Operator'].apply(lambda x: 'MTN' if x.upper() == 'MTN' else x.title())
    df = df[df['Operator'].isin(['Vodacom', 'MTN', 'Rain', 'Telkom'])]
    
    # 修复 Sentiment 大小写
    df['Sentiment'] = df['Sentiment'].apply(lambda s: 'Positive' if 'positive' in str(s).lower() else 'Negative')

    def classify_product(row):
        text = str(row['Service_Type']).lower() + " " + str(row.get('Content', '')).lower()
        op = str(row['Operator'])
        if any(x in text for x in ['fibre', 'fiber', 'openserve', 'vumatel']): return 'Fibre'
        if any(x in text for x in ['router', 'wifi', 'home', 'cpe', 'fixed', 'rain one']): return 'FWA'
        if any(x in text for x in ['phone', 'mobile', 'sim', 'roaming', 'upgrade']): return 'MBB'
        return 'FWA' if op == 'Rain' else 'MBB'

    df['Service_Type'] = df.apply(classify_product, axis=1)
    df['Date'] = pd.to_datetime(df['Date'])
    df['Day'] = df['Date'].dt.date
    df['Urgency'] = pd.to_numeric(df['Urgency'], errors='coerce').fillna(0)
    return df

def plot_to_buffer():
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=Config.IMG_DPI, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    return buf

# ===========================
# 🧠 核心：深度思考 AI 综述 (保留 Prompt)
# ===========================
def generate_deep_insight_summary(df):
    print("🧠 生成深度 AI 思考综述 (中文)...")
    dossier = f"报告日期: {df['Day'].max()}\n"
    dossier += f"总评论数: {len(df)}\n\n"

    for op in df['Operator'].unique():
        op_df = df[df['Operator'] == op]
        neg_df = op_df[op_df['Sentiment']=='Negative']
        neg_count = len(neg_df)
        pos_count = len(op_df[op_df['Sentiment']=='Positive'])

        dossier += f"运营商: {op.upper()}\n"
        dossier += f"  - 数据: {neg_count} 条投诉 vs {pos_count} 条表扬\n"

        if neg_count > 0:
            top_issues = neg_df['L2_Issue'].value_counts().head(3).to_dict()
            dossier += f"  - Top 3 具体故障: {top_issues}\n"
            if not neg_df['Service_Type'].empty:
                top_prod = neg_df['Service_Type'].value_counts().idxmax()
                dossier += f"  - 重灾区产品: {top_prod}\n"
        dossier += "\n"

    # --- 你的 Prompt 开始 ---
    prompt = f"""
    你是一位南非电信市场的首席战略分析师。请根据以下本周舆情数据，写一份中文的《执行摘要》。

    数据档案:
    {dossier}

    写作要求：
    1. **市场总览**: 一句话评价本周整体市场情绪（谁表现最差？谁相对稳定？）。
    2. **运营商深度洞察**: 不要只罗列数字。请分析“为什么”。
       - 例如：如果 Rain 的问题集中在 FWA 且全是“网速慢”，请分析这是否意味着“基站拥堵”或“超卖”。
       - 例如：如果 Vodacom 全是 Billing 问题，请分析是否可能存在“系统性计费错误”。
    3. **策略建议**: 针对每个运营商最严重的问题，给出一条简短的改进建议。
    4. **格式**: 使用 HTML 格式（<br>换行，<b>加粗关键点</b>），语言简练专业。不要写废话。
    """
    # --- 你的 Prompt 结束 ---

    try:
        client = OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)
        response = client.chat.completions.create(
            model=Config.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"AI 生成失败: {e}")
        return "AI 分析服务暂时不可用。"

# ===========================
# 📊 绘图函数集 (保留原有逻辑)
# ===========================
def plot_trend(df):
    operators = sorted(df['Operator'].unique())
    rows = (len(operators) + 1) // 2
    fig, axes = plt.subplots(rows, 2, figsize=(10, 3.5 * rows))
    axes = axes.flatten() if len(operators) > 1 else [axes]

    for i, op in enumerate(operators):
        ax = axes[i]
        op_data = df[df['Operator'] == op]
        trend = op_data.groupby(['Day', 'Sentiment']).size().reset_index(name='Count')
        if not trend.empty:
            sns.lineplot(data=trend, x='Day', y='Count', hue='Sentiment',
                         palette=Config.SENTIMENT_COLORS, marker='o', ax=ax)
            ax.set_title(op, fontweight='bold', color=Config.BRAND_COLORS.get(op, '#333'))
            ax.set_xlabel('')
            if i == 0: ax.legend(title='', loc='upper left', frameon=False)
            else:
                if ax.get_legend(): ax.get_legend().remove()
        else:
            ax.text(0.5, 0.5, "No Data", ha='center')
    if len(operators) > 1:
        for j in range(i + 1, len(axes)): fig.delaxes(axes[j])
    plt.tight_layout()
    return plot_to_buffer()

def plot_category(df):
    plt.figure(figsize=(8, 4))
    neg_df = df[df['Sentiment'] == 'Negative']
    if neg_df.empty: return None
    cat_data = pd.crosstab(neg_df['Operator'], neg_df['L1_Category'], normalize='index') * 100
    if not cat_data.empty:
        cat_data.plot(kind='bar', stacked=True, colormap='Spectral', width=0.8, ax=plt.gca())
        plt.title('Complaint Categories', fontweight='bold')
        plt.legend(bbox_to_anchor=(1, 1), frameon=False, fontsize='small')
        plt.xticks(rotation=0)
        sns.despine()
        return plot_to_buffer()
    return None

def plot_deep_dive(df):
    neg_df = df[df['Sentiment'] == 'Negative']
    if neg_df.empty: return None
    operators = sorted(neg_df['Operator'].unique())
    rows = (len(operators) + 1) // 2
    fig, axes = plt.subplots(rows, 2, figsize=(10, 3.5 * rows))
    axes = axes.flatten() if len(operators) > 1 else [axes]

    for i, op in enumerate(operators):
        ax = axes[i]
        op_data = neg_df[neg_df['Operator'] == op]
        if not op_data.empty:
            top_l1 = op_data['L1_Category'].value_counts().idxmax()
            target = op_data[op_data['L1_Category'] == top_l1]
            counts = target['L2_Issue'].value_counts().head(5).reset_index()
            counts.columns = ['Issue', 'Count']
            counts = counts[counts['Count'] >= 3]

            color = Config.BRAND_COLORS.get(op, '#333')
            if not counts.empty:
                sns.barplot(data=counts, x='Count', y='Issue', ax=ax, color=color)
                ax.set_title(f"{op}: {top_l1}", fontweight='bold', color=color, fontsize=10)
                ax.set_xlabel('')
                ax.set_ylabel('')
                ax.tick_params(axis='y', labelsize=8)
            else:
                ax.text(0.5, 0.5, "No Major Issues", ha='center')
                ax.set_title(op, color=color)
    if len(operators) > 1:
        for j in range(i + 1, len(axes)): fig.delaxes(axes[j])
    plt.tight_layout()
    return plot_to_buffer()

def generate_cluster_table(df):
    target = df[(df['Location'] != 'Unknown') & (df['Sentiment'] == 'Negative')]
    if target.empty: return "<tr><td colspan='5'>No clusters.</td></tr>"
    clusters = target.groupby(['Day', 'Operator', 'Location', 'L2_Issue']).size().reset_index(name='count')
    clusters = clusters[clusters['count'] >= 2].sort_values('count', ascending=False).head(5)

    html = ""
    if not clusters.empty:
        for _, row in clusters.iterrows():
            c = Config.BRAND_COLORS.get(row['Operator'], '#333')
            html += f"""
            <tr style="border-bottom:1px solid #eee;">
                <td style="padding:5px;">{row['Day']}</td>
                <td style="color:{c};font-weight:bold;padding:5px;">{row['Operator']}</td>
                <td style="padding:5px;">{row['Location']}</td>
                <td style="padding:5px;">{row['L2_Issue']}</td>
                <td style="padding:5px;"><span style="background:#e74c3c;color:#fff;padding:2px 6px;border-radius:4px;font-size:11px;">{row['count']}</span></td>
            </tr>"""
    else:
        html = "<tr><td colspan='5' style='padding:5px; color:green;'>✅ No clusters.</td></tr>"
    return html

def generate_customer_voice(df):
    print("🗣️ 提取客户原声 (Top 3)...")
    # 筛选负面评论
    neg_df = df[df['Sentiment'] == 'Negative']
    if neg_df.empty: return "No negative reviews."

    html_cards = ""
    # 按运营商排序确保顺序固定
    operators = sorted(neg_df['Operator'].unique())

    for op in operators:
        op_data = neg_df[neg_df['Operator'] == op]
        if op_data.empty: continue

        # --- 修改开始 ---
        # 逻辑变更：不再只取 Top Issue 的一条，而是取该运营商最新的 3 条负面评论
        # 如果你的 analyzer.py 未来实现了 Urgency 打分，这里也会自动优先展示高优先级的
        # 目前默认按时间排序（因为爬虫是从第一页开始抓的，通常是按时间倒序）
        target_reviews = op_data.sort_values('Urgency', ascending=False).head(3)
        
        for _, row in target_reviews.iterrows():
            # 动态获取每条评论的具体问题，而不是笼统的显示 Top Issue
            issue = row.get('L2_Issue', 'General Issue')
            
            # 截取内容
            content_preview = str(row.get('Content', ''))
            if len(content_preview) > 150:
                quote = content_preview[:150] + "..."
            else:
                quote = content_preview
            
            # 构建链接
            url = str(row.get('Url', ''))
            link_html = ''
            if url.startswith('http'):
                 link_html = f'<a href="{url}" target="_blank" style="color:#007bff;text-decoration:none;font-size:12px;">[点击查看原文]</a>'

            # 获取品牌颜色
            color = Config.BRAND_COLORS.get(op, '#333')

            # 组装 HTML 卡片
            html_cards += f"""
            <div style="background:#fff; border-left:4px solid {color}; padding:12px; margin-bottom:12px; border-radius:4px; box-shadow:0 1px 2px rgba(0,0,0,0.05);">
                <div style="font-size:14px; font-weight:bold; color:{color}; margin-bottom:6px;">
                    {op} • {issue}
                </div>
                <div style="font-size:13px; font-style:italic; color:#555; margin-bottom:8px; line-height:1.4;">
                    "{quote}"
                </div>
                {link_html}
            </div>
            """
        # --- 修改结束 ---

    return html_cards

def send_report(df, ai_summary, buf_trend, buf_cat, buf_deep, voice_html, cluster_html):
    print("📧 组装邮件...")
    msg = MIMEMultipart('related')
    msg['Subject'] = f"📊 HelloPeter 电信舆情周报: {df['Day'].max()}"
    msg['From'] = Config.EMAIL_SENDER
    msg['To'] = ", ".join(Config.EMAIL_RECEIVERS)

    # --- HTML 模板保留 ---
    html_body = f"""
    <html>
    <body style="font-family: 'Microsoft YaHei', Arial, sans-serif; color:#333; max-width:800px; line-height:1.6;">
        <h2 style="color:#2c3e50; border-bottom:3px solid #3498db; padding-bottom:10px;">🇿🇦 HelloPeter 电信舆情深度分析</h2>

        <div style="background:#f0f7ff; padding:20px; border-radius:8px; border-left:5px solid #0072CE; margin-bottom:25px;">
            <b style="color:#0072CE; font-size:16px;">🤖 AI 首席分析师综述:</b><br>
            <div style="margin-top:10px; font-size:14px;">{ai_summary}</div>
        </div>

        <h3 style="margin-top:30px; color:#34495e; border-left:4px solid #FFCB05; padding-left:10px;">2. 舆情走势 (正向 vs 负向)</h3>
        <p style="font-size:12px; color:gray;">红线代表投诉，绿线代表表扬。分运营商展示。</p>
        <img src="cid:trend_img" style="width:100%; border:1px solid #eee; border-radius:5px;">

        <h3 style="margin-top:30px; color:#34495e; border-left:4px solid #FFCB05; padding-left:10px;">3. 投诉类别占比</h3>
        <p style="font-size:12px; color:gray;">网络、计费、服务等问题的构成比例。</p>
        <img src="cid:cat_img" style="width:100%; border:1px solid #eee; border-radius:5px;">

        <h3 style="margin-top:30px; color:#34495e; border-left:4px solid #FFCB05; padding-left:10px;">4. 核心痛点下钻 (过滤低频)</h3>
        <p style="font-size:12px; color:gray;">仅展示该运营商投诉量 >= 3 的具体技术/业务故障。</p>
        <img src="cid:deep_img" style="width:100%; border:1px solid #eee; border-radius:5px;">

        <h3 style="margin-top:30px; color:#34495e; border-left:4px solid #FFCB05; padding-left:10px;">5. 客户原声 (典型投诉)</h3>
        <div style="background:#f9f9f9; padding:15px; border-radius:5px;">
            {voice_html}
        </div>

        <h3 style="margin-top:30px; color:#34495e; border-left:4px solid #FFCB05; padding-left:10px;">6. 集中爆发监控 (Cluster Monitor)</h3>
        <table style="width:100%; border-collapse:collapse; font-size:13px;">
            <tr style="background:#fff8e1;">
                <th style="padding:8px;text-align:left;">日期</th>
                <th style="padding:8px;text-align:left;">运营商</th>
                <th style="padding:8px;text-align:left;">地点</th>
                <th style="padding:8px;text-align:left;">核心问题</th>
                <th style="padding:8px;text-align:left;">爆发量</th>
            </tr>
            {cluster_html}
        </table>

        <p style="font-size:12px; color:#999; margin-top:40px; text-align:center;">
            Automated by Telecom AI Analyst • {datetime.now().strftime('%Y-%m-%d %H:%M')}
        </p>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_body, 'html'))

    def attach_image(buffer, content_id):
        if buffer is None: return
        img = MIMEImage(buffer.read())
        img.add_header('Content-ID', content_id)
        msg.attach(img)

    attach_image(buf_trend, '<trend_img>')
    attach_image(buf_cat, '<cat_img>')
    attach_image(buf_deep, '<deep_img>')

    try:
        server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT)
        server.starttls()
        server.login(Config.EMAIL_SENDER, Config.EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("✅ 邮件发送成功！")
    except Exception as e:
        print(f"❌ 发送失败: {e}")
