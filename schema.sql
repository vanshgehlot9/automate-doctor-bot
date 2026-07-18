-- Supabase Schema Migration

-- Tenants Table
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    hospital_name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    email TEXT NOT NULL,
    address TEXT,
    whatsapp_number_id TEXT,
    is_active BOOLEAN DEFAULT true,
    clinic_address TEXT,
    latitude FLOAT,
    longitude FLOAT,
    room_floor TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Doctors Table
CREATE TABLE doctors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    specialization TEXT NOT NULL,
    qualifications JSONB DEFAULT '[]'::jsonb,
    experience_years INTEGER NOT NULL,
    languages JSONB DEFAULT '[]'::jsonb,
    consultation_fee FLOAT NOT NULL,
    availability_schedule JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Patients Table
CREATE TABLE patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    gender TEXT NOT NULL,
    dob DATE NOT NULL,
    blood_group TEXT,
    mobile_number TEXT NOT NULL,
    email TEXT,
    address TEXT,
    emergency_contact TEXT,
    family_members JSONB DEFAULT '[]'::jsonb,
    insurance_details JSONB DEFAULT '{}'::jsonb,
    allergies JSONB DEFAULT '[]'::jsonb,
    chronic_diseases JSONB DEFAULT '[]'::jsonb,
    medical_history JSONB DEFAULT '[]'::jsonb,
    current_medications JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Appointments Table
CREATE TABLE appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id UUID REFERENCES doctors(id) ON DELETE CASCADE,
    appointment_date DATE NOT NULL,
    appointment_time TEXT NOT NULL,
    appointment_end TEXT NOT NULL,
    slot_id TEXT,
    reason_for_visit TEXT NOT NULL,
    status TEXT DEFAULT 'Pending',
    is_walk_in BOOLEAN DEFAULT false,
    queue_number INTEGER,
    follow_up_to TEXT,
    prescription_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Note: You may need to create similar tables for users, ipd, laboratory, prescriptions, schedules, and reports based on their respective models.

-- Row Level Security (RLS) can be enabled if accessing directly from frontend.
-- Example:
-- ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE doctors ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;

-- If using backend to access via Service Role key, RLS policies are bypassed by default for that key,
-- but it's good practice to set them up for frontend access.

-- Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY, -- References auth.users(id)
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit Logs Table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID,
    action TEXT NOT NULL,
    entity TEXT NOT NULL,
    entity_id TEXT,
    details JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Beds Table (IPD)
CREATE TABLE beds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    ward_name TEXT NOT NULL,
    bed_number TEXT NOT NULL,
    bed_type TEXT NOT NULL,
    status TEXT DEFAULT 'Available',
    daily_rate FLOAT NOT NULL,
    current_patient_id UUID REFERENCES patients(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Admissions Table (IPD)
CREATE TABLE admissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    bed_id UUID REFERENCES beds(id),
    admission_date TIMESTAMP WITH TIME ZONE NOT NULL,
    discharge_date TIMESTAMP WITH TIME ZONE,
    reason_for_admission TEXT,
    status TEXT DEFAULT 'Admitted',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Lab Tests Table
CREATE TABLE lab_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id UUID REFERENCES doctors(id),
    test_name TEXT NOT NULL,
    test_date TIMESTAMP WITH TIME ZONE NOT NULL,
    status TEXT DEFAULT 'Pending',
    results JSONB DEFAULT '{}'::jsonb,
    report_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Medical Reports Table
CREATE TABLE medical_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    report_type TEXT,
    category TEXT,
    report_date TEXT,
    ocr_text TEXT,
    structured_data JSONB DEFAULT '{}'::jsonb,
    ai_summary TEXT,
    ai_recommendation TEXT,
    tags JSONB DEFAULT '[]'::jsonb,
    status TEXT DEFAULT 'Pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Prescriptions Table
CREATE TABLE prescriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id UUID REFERENCES doctors(id),
    doctor_name TEXT,
    prescription_date TEXT,
    medicines JSONB DEFAULT '[]'::jsonb,
    notes TEXT,
    status TEXT DEFAULT 'Needs Verification',
    verified_by UUID,
    verified_at TIMESTAMP WITH TIME ZONE,
    approved_by UUID,
    approved_at TIMESTAMP WITH TIME ZONE,
    versions JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Doctor Schedules Table
CREATE TABLE doctor_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    doctor_id UUID REFERENCES doctors(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL,
    is_working_day BOOLEAN DEFAULT true,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    break_start TEXT,
    break_end TEXT,
    slot_duration_minutes INTEGER DEFAULT 30,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Doctor Holidays Table
CREATE TABLE doctor_holidays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id UUID REFERENCES doctors(id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Subscriptions Table
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    plan_name TEXT NOT NULL,
    monthly_price INTEGER NOT NULL,
    setup_fee INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    billing_cycle TEXT NOT NULL DEFAULT 'monthly',
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    renewal_date TIMESTAMP WITH TIME ZONE NOT NULL,
    payment_reference TEXT NOT NULL UNIQUE,
    order_id TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tenant Settings Table
CREATE TABLE tenant_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE UNIQUE,
    setup_completed BOOLEAN DEFAULT false,
    whatsapp_connected BOOLEAN DEFAULT false,
    notification_preferences JSONB DEFAULT '{"email": true, "sms": false, "whatsapp": true}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- WhatsApp Accounts Table
CREATE TABLE whatsapp_accounts (
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
