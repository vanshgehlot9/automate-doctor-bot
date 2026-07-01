export interface Tenant {
  id: string;
  name: string;
  hospital_name: string;
  phone_number: string;
  email: string;
  address: string | null;
  whatsapp_number_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Doctor {
  id: string;
  tenant_id: string;
  name: string;
  specialization: string;
  qualifications: string[];
  experience_years: number;
  languages: string[];
  consultation_fee: number;
  availability_schedule: Record<string, any>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Patient {
  id: string;
  tenant_id: string;
  name: string;
  phone: string;
  dob: string | null;
  gender: string | null;
  blood_group: string | null;
  allergies: string[];
  created_at: string;
  updated_at: string;
}

export interface Appointment {
  id: string;
  tenant_id: string;
  doctor_id: string;
  patient_id: string;
  appointment_date: string;
  appointment_time: string;
  status: 'scheduled' | 'completed' | 'cancelled' | 'no_show' | 'pending' | 'confirmed' | 'waiting';
  reason: string | null;
  notes: string | null;
  prescription_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface LaboratoryTest {
  id: string;
  tenant_id: string;
  patient_id: string;
  doctor_id: string | null;
  test_name: string;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  result_summary: string | null;
  report_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface DoctorSchedule {
  id: string;
  doctor_id: string;
  tenant_id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  break_start: string | null;
  break_end: string | null;
  slot_duration_minutes: number;
  buffer_minutes: number;
  created_at: string;
  updated_at: string;
}

export interface DoctorHoliday {
  id: string;
  doctor_id: string;
  tenant_id: string;
  date: string;
  reason: string;
  type: "full_day" | "partial_day";
  start_time: string | null;
  end_time: string | null;
  created_at: string;
  updated_at: string;
}
