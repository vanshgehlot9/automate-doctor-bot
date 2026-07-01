import axios from "axios";
import { auth } from "./firebase";

const RAW_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_ROOT = RAW_BASE_URL.replace(/\/$/, "");
const ADMIN_BASE_URL = `${API_ROOT}/api/v1`;

export const api = axios.create({
  baseURL: ADMIN_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Intercept requests and attach the Firebase ID token and Tenant ID
api.interceptors.request.use(async (config) => {
  if (auth.currentUser) {
    const token = await auth.currentUser.getIdToken();
    config.headers.Authorization = `Bearer ${token}`;
  }
  
  if (typeof window !== "undefined") {
    if (!config.headers["x-tenant-id"]) {
      const tenantId = localStorage.getItem("tenantId");
      if (tenantId) {
        config.headers["x-tenant-id"] = tenantId;
      }
    }
  }

  return config;
}, (error) => {
  return Promise.reject(error);
});

import { Tenant, Doctor, Patient, Appointment, LaboratoryTest } from "@/types/api";

export const getTenants = async (): Promise<Tenant[]> => {
  return (await api.get("/tenants/")).data;
};

export const getDoctors = async (): Promise<Doctor[]> => {
  return (await api.get("/doctors/")).data;
};

export const getPatients = async (): Promise<Patient[]> => {
  return (await api.get("/patients/")).data;
};

export const getAppointments = async (): Promise<Appointment[]> => {
  return (await api.get("/appointments/")).data;
};

export const getLaboratoryTests = async (): Promise<LaboratoryTest[]> => {
  return (await api.get("/laboratory/tests")).data;
};

// --- Creation Endpoints ---

export const createTenant = async (data: Partial<Tenant>): Promise<Tenant> => {
  return (await api.post("/tenants/", data)).data;
};

export const getUsers = async (): Promise<any[]> => {
  return (await api.get("/users/")).data;
};

export const createUser = async (data: { email: string; name: string; role: string; tenant_id?: string; phone?: string }): Promise<any> => {
  return (await api.post("/users/", data)).data;
};

export const createDoctor = async (data: Partial<Doctor>): Promise<Doctor> => {
  return (await api.post("/doctors/", data, {
    headers: data.tenant_id ? { "x-tenant-id": data.tenant_id } : undefined
  })).data;
};

export const deleteUser = async (uid: string, tenantId?: string): Promise<void> => {
  await api.delete(`/users/${uid}`, {
    headers: tenantId ? { "x-tenant-id": tenantId } : undefined
  });
};

export const deleteDoctor = async (id: string, tenantId?: string): Promise<void> => {
  await api.delete(`/doctors/${id}`, {
    headers: tenantId ? { "x-tenant-id": tenantId } : undefined
  });
};

export const getDoctorSchedules = async (doctorId: string): Promise<any[]> => {
  return (await api.get(`/schedules/${doctorId}`)).data;
};

export const createDoctorSchedule = async (data: any): Promise<any> => {
  return (await api.post("/schedules/", data, {
    headers: data.tenant_id ? { "x-tenant-id": data.tenant_id } : undefined
  })).data;
};

export const createDoctorHoliday = async (data: any): Promise<any> => {
  return (await api.post("/schedules/holidays", data, {
    headers: data.tenant_id ? { "x-tenant-id": data.tenant_id } : undefined
  })).data;
};

// Add more API endpoints matching the python backend (laboratory.py, patients, etc.) as needed

export const getAvailableSlots = async (doctorId: string, targetDate: string, tenantId?: string): Promise<any[]> => {
  return (await api.get(`/schedules/${doctorId}/slots`, {
    params: { target_date: targetDate },
    headers: tenantId ? { "x-tenant-id": tenantId } : undefined
  })).data;
};

export const createAppointment = async (data: Partial<Appointment>): Promise<Appointment> => {
  return (await api.post("/appointments/", data, {
    headers: data.tenant_id ? { "x-tenant-id": data.tenant_id } : undefined
  })).data;
};

export const updateAppointment = async (id: string, data: Partial<Appointment>): Promise<Appointment> => {
  return (await api.put(`/appointments/${id}`, data, {
    headers: data.tenant_id ? { "x-tenant-id": data.tenant_id } : undefined
  })).data;
};

// --- Vendors ---
export const fetchVendors = async (): Promise<any[]> => {
  return (await api.get("/vendors/")).data;
};

export const createVendor = async (data: any): Promise<any> => {
  return (await api.post("/vendors/", data, {
    headers: data.tenant_id ? { "x-tenant-id": data.tenant_id } : undefined
  })).data;
};

export const updateVendor = async (id: string, data: any): Promise<any> => {
  return (await api.put(`/vendors/${id}`, data, {
    headers: data.tenant_id ? { "x-tenant-id": data.tenant_id } : undefined
  })).data;
};

export const deleteVendor = async (id: string, tenantId?: string): Promise<void> => {
  await api.delete(`/vendors/${id}`, {
    headers: tenantId ? { "x-tenant-id": tenantId } : undefined
  });
};

// --- Prescriptions ---
export const getPrescription = async (id: string, tenantId?: string): Promise<any> => {
  return (await api.get(`/prescriptions/${id}`, {
    headers: tenantId ? { "x-tenant-id": tenantId } : undefined
  })).data;
};

export const verifyPrescription = async (id: string, data: any, tenantId?: string): Promise<any> => {
  return (await api.post(`/prescriptions/${id}/verify`, data, {
    headers: tenantId ? { "x-tenant-id": tenantId } : undefined
  })).data;
};

// Legacy
export const fetchMyHotel = async (): Promise<any> => {
  return null;
};

export const fetchCurrentUser = async (): Promise<any> => {
  return null;
};
