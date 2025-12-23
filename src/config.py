import os

# 尝试加载本地 .env (用于本地调试)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class Config:
    # 基础路径
    RAW_FILE = "raw_reviews.csv"
    ANALYZED_FILE = "analyzed_reviews.csv"
    
    # 爬虫配置
    TARGET_OPERATORS = ["vodacom", "mtn", "telkom", "rain-internet-service-provider"]
    DAYS_TO_SCRAPE = 7
    
    # LLM 配置 (从环境变量读取)
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
    
    # 邮件配置 (从环境变量读取)
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    # 支持多个接收人，用逗号分隔
    EMAIL_RECEIVERS = os.getenv("EMAIL_RECEIVERS", "").split(",")
    
    # 视觉配置 (保留你的配色)
    BRAND_COLORS = {
        'Vodacom': '#E60000', 'MTN': '#FFCB05',
        'Rain': '#00C4B4', 'Telkom': '#0072CE',
        'Unknown': '#999999'
    }
    SENTIMENT_COLORS = {'Negative': '#D32F2F', 'Positive': '#388E3C'}
    IMG_DPI = 70
