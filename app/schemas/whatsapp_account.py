from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class WhatsAppAccountBase(BaseModel):
    tenant_id: str
    bot_name: str
    bot_type: str
    phone_number: str
    phone_number_id: str
    access_token: str
    private_key_path: str
    public_key_path: str
    verify_token: Optional[str] = None
    status: str = "active"

class WhatsAppAccountCreate(WhatsAppAccountBase):
    pass

class WhatsAppAccount(WhatsAppAccountBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True
