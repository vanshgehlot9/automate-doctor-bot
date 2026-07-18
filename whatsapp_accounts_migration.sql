-- WhatsApp Accounts Table Migration
-- Run this to update your database for the multi-bot architecture

CREATE TABLE IF NOT EXISTS whatsapp_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    bot_name TEXT NOT NULL,
    bot_type TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    phone_number_id TEXT NOT NULL UNIQUE,
    access_token TEXT NOT NULL,
    private_key_path TEXT NOT NULL,
    public_key_path TEXT NOT NULL,
    verify_token TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
