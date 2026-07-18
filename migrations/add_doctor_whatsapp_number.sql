-- Migration: Add WhatsApp number to doctors table
-- Run this in Supabase SQL Editor

ALTER TABLE doctors ADD COLUMN IF NOT EXISTS whatsapp_number TEXT;

-- Optional: index for fast lookup when doctor messages the bot
CREATE INDEX IF NOT EXISTS idx_doctors_whatsapp_number ON doctors(whatsapp_number);
