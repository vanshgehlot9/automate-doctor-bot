from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Healthcare AI Operating System"
    API_V1_STR: str = "/api/v1"
    
    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    
    # WhatsApp
    WHATSAPP_TOKEN: Optional[str] = None
    WHATSAPP_VERIFY_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_BUSINESS_ACCOUNT_ID: Optional[str] = None
    WHATSAPP_FLOW_ID: Optional[str] = None
    WHATSAPP_REGISTRATION_FLOW_ID: Optional[str] = None
    
    # Default tenant (single-tenant mode)
    DEFAULT_TENANT_ID: str = "default"
    
    # AI (Gemini)
    GEMINI_API_KEY: Optional[str] = None
    
    # AWS Textract
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
