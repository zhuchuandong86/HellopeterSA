import os
import sys

# 如果在本地运行，尝试加载 .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class Config:
    # 爬虫配置
    TARGET_OPERATORS = ["vodacom", "mtn", "telkom", "rain-internet-service-provider"]
    DAYS_TO_SCRAPE = 7
    
    # LLM 配置
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

    # 邮件配置
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    # 接收者可以配置为一个逗号分隔的字符串
    EMAIL_RECEIVERS = os.getenv("EMAIL_RECEIVERS", "").split(",")

    # 检查必要配置
    @staticmethod
    def validate():
        required = ["LLM_API_KEY", "EMAIL_SENDER", "EMAIL_PASSWORD", "EMAIL_RECEIVERS"]
        missing = [key for key in required if not os.getenv(key)]
        if missing:
            print(f"❌ 缺少环境变量: {', '.join(missing)}")
            sys.exit(1)
