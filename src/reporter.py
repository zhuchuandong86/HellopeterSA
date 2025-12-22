import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime
from src.config import Config

# 设置 matplotlib 后端，防止无头环境报错
plt.switch_backend('Agg')

def clean_data(df):
    # 简单的数据清洗逻辑
    op_map = {
        'rain-internet-service-provider': 'Rain',
        'mtn-service-provider': 'MTN', 
        'telkom-sa': 'Telkom',
        'vodacom-provider': 'Vodacom'
    }
    df['Operator'] = df['Operator'].replace(op_map)
    df['Operator'] = df['Operator'].apply(lambda x: 'MTN' if str(x).upper()=='MTN' else str(x).title())
    return df

def create_plots(df):
    imgs = {}
    
    # 图1：趋势图
    plt.figure(figsize=(10, 4))
    if not df.empty:
        trend = df.groupby([df['Date'].dt.date, 'Operator']).size().unstack().fillna(0)
        sns.lineplot(data=trend)
        plt.title("Review Volume Trend (7 Days)")
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    imgs['trend'] = buf
    plt.close()
    
    return imgs

def send_email(df, summary, imgs):
    print("📧 [Step 3] 发送邮件...")
    msg = MIMEMultipart('related')
    msg['Subject'] = f"📊 Hellopeter Weekly Report: {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = Config.EMAIL_SENDER
    msg['To'] = ", ".join(Config.EMAIL_RECEIVERS)

    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>🇿🇦 Telecom Weekly Monitor</h2>
            <div style="background:#f4f4f4; padding:15px; border-left: 5px solid #007bff;">
                {summary}
            </div>
            <h3>Trend Analysis</h3>
            <img src="cid:trend_img" style="width:100%; max-width:600px;">
            <p>Total Reviews: {len(df)}</p>
        </body>
    </html>
    """
    msg.attach(MIMEText(html, 'html'))

    # 附件图片
    if 'trend' in imgs:
        img = MIMEImage(imgs['trend'].read())
        img.add_header('Content-ID', '<trend_img>')
        msg.attach(img)

    try:
        server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT)
        server.starttls()
        server.login(Config.EMAIL_SENDER, Config.EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("✅ 邮件发送成功！")
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
