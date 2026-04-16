from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "change-me-in-production"
    ALLOWED_ORIGINS: List[str] = ["*"]

    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    DATABASE_URL: str = ""

    REDIS_URL: str = "redis://localhost:6379"

    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "agentdb-media"
    R2_PUBLIC_URL: str = ""

    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID_BASIC: str = ""
    STRIPE_PRICE_ID_PRO: str = ""

    COINBASE_COMMERCE_API_KEY: str = ""
    COINBASE_COMMERCE_WEBHOOK_SECRET: str = ""

    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    TRIAL_DAYS: int = 3
    WEEKLY_PRICE_GBP: float = 10.00

    RATE_LIMIT_TRIAL: int = 100
    RATE_LIMIT_BASIC: int = 1000
    RATE_LIMIT_PRO: int = 99999

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
