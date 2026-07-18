from typing import List, Optional
from datetime import datetime, date, timedelta
from app.db.supabase import db
from app.db.retry import with_retry
from app.schemas.schedule import (
    DoctorScheduleCreate,
    DoctorScheduleInDB,
    DoctorScheduleUpdate,
    DoctorHolidayCreate,
    DoctorHolidayInDB,
    AppointmentSlotBase,
    SlotStatus,
    HolidayType
)
from app.services.slot_generator import SlotGeneratorService
import uuid

class ScheduleService:
    @staticmethod
    def create_schedule(tenant_id: str, schedule_in: DoctorScheduleCreate) -> DoctorScheduleInDB:
        if not db: return None
        
        data = schedule_in.dict()
        data['tenant_id'] = tenant_id
        data.pop('buffer_minutes', None)
        
        # We must upsert or delete the old schedule for this day to avoid duplicates
        existing = with_retry(lambda: db.table("doctor_schedules").select("id").eq("doctor_id", schedule_in.doctor_id).eq("day_of_week", schedule_in.day_of_week).execute())()
        if existing.data:
            response = with_retry(lambda: db.table("doctor_schedules").update(data).eq("id", existing.data[0]['id']).execute())()
        else:
            response = with_retry(lambda: db.table("doctor_schedules").insert(data).execute())()
            
        if response.data:
            return DoctorScheduleInDB(**response.data[0])
        return None

    @staticmethod
    def get_doctor_schedules(tenant_id: str, doctor_id: str) -> List[DoctorScheduleInDB]:
        if not db: return []
        
        response = with_retry(lambda: db.table("doctor_schedules").select("*").eq("tenant_id", tenant_id).eq("doctor_id", doctor_id).execute())()
        if response.data:
            return [DoctorScheduleInDB(**row) for row in response.data]
        return []
    
    @staticmethod
    def create_holiday(tenant_id: str, holiday_in: DoctorHolidayCreate) -> DoctorHolidayInDB:
        if not db: return None
        
        data = holiday_in.dict()
        data['date'] = data['date'].isoformat()
        data['tenant_id'] = tenant_id
        
        response = with_retry(lambda: db.table("doctor_holidays").insert(data).execute())()
        
        if response.data:
            ret_data = response.data[0]
            if isinstance(ret_data.get('date'), str):
                ret_data['date'] = datetime.strptime(ret_data['date'], "%Y-%m-%d").date()
            return DoctorHolidayInDB(**ret_data)
        return None

    @staticmethod
    def get_doctor_holidays(tenant_id: str, doctor_id: str, target_date: date) -> List[DoctorHolidayInDB]:
        if not db: return []
        
        response = with_retry(lambda: db.table("doctor_holidays").select("*").eq("tenant_id", tenant_id).eq("doctor_id", doctor_id).eq("date", target_date.isoformat()).execute())()
        holidays = []
        if response.data:
            for row in response.data:
                if isinstance(row.get('date'), str):
                    row['date'] = datetime.strptime(row['date'], "%Y-%m-%d").date()
                holidays.append(DoctorHolidayInDB(**row))
        return holidays

    @staticmethod
    def get_available_slots(tenant_id: str, doctor_id: str, target_date: date) -> List[AppointmentSlotBase]:
        """
        Dynamically calculates available slots for a given doctor on a given date.
        Falls back to the doctor's availability_schedule field when no schedule
        documents have been created yet.
        """
        # 1. Try structured schedule documents first
        day_of_week = target_date.weekday()
        schedules = ScheduleService.get_doctor_schedules(tenant_id, doctor_id)
        schedule_for_day = next((s for s in schedules if s.day_of_week == day_of_week), None)

        if schedule_for_day:
            # 2a. Use structured schedule (existing path)
            holidays = ScheduleService.get_doctor_holidays(tenant_id, doctor_id, target_date)
            generated_slots = SlotGeneratorService.generate_slots(schedule_for_day, target_date, holidays)
        else:
            # 2b. Fallback: read availability_schedule from the doctor document
            generated_slots = ScheduleService._slots_from_doctor_availability(
                tenant_id, doctor_id, target_date)

        if not generated_slots:
            return []

        # 3. Filter out already-booked slots
        if not db: return []
        
        response = with_retry(lambda: db.table("appointments").select("appointment_time").eq("tenant_id", tenant_id).eq("doctor_id", doctor_id).eq("appointment_date", target_date.isoformat()).in_("status", ["scheduled", "confirmed", "waiting", "checked-in", "in consultation", "completed"]).execute())()
        
        booked_times = {row['appointment_time'][:5] for row in response.data} if response.data else set()
        
        # Alternatively we can check appointment_slots table if we migrate that. But appointments works for our fallback setup.
        
        return [s for s in generated_slots if s.start_time not in booked_times]

    # ── Fallback slot generator ─────────────────────────────────────────────────
    DAY_NAMES = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    @staticmethod
    def _slots_from_doctor_availability(
        tenant_id: str, doctor_id: str, target_date: date,
        slot_minutes: int = 30, buffer_minutes: int = 0
    ) -> List[AppointmentSlotBase]:
        """
        Generate slots from the doctor document's availability_schedule dict.
        Format: {"monday": ["09:00-17:00"], "wednesday": ["10:00-14:00"]}
        Each range produces 30-minute slots (configurable via slot_minutes).
        """
        from app.services.doctor_service import DoctorService
        doctor = DoctorService.get_doctor(tenant_id, doctor_id)
        if not doctor or not doctor.availability_schedule:
            return []

        day_name = ScheduleService.DAY_NAMES[target_date.weekday()]
        ranges = doctor.availability_schedule.get(day_name, [])
        if not ranges:
            return []

        slots: List[AppointmentSlotBase] = []
        slot_td   = timedelta(minutes=slot_minutes)
        buffer_td = timedelta(minutes=buffer_minutes)

        for time_range in ranges:
            try:
                start_str, end_str = time_range.split('-')
                start_h, start_m = map(int, start_str.strip().split(':'))
                end_h,   end_m   = map(int, end_str.strip().split(':'))
            except Exception:
                continue  # skip malformed entries

            current = timedelta(hours=start_h, minutes=start_m)
            end_td  = timedelta(hours=end_h,   minutes=end_m)

            while current + slot_td <= end_td:
                slot_end = current + slot_td
                start_s  = f"{int(current.total_seconds()//3600):02d}:{int((current.total_seconds()%3600)//60):02d}"
                end_s    = f"{int(slot_end.total_seconds()//3600):02d}:{int((slot_end.total_seconds()%3600)//60):02d}"
                slots.append(AppointmentSlotBase(
                    doctor_id=doctor_id,
                    tenant_id=tenant_id,
                    date=target_date,
                    start_time=start_s,
                    end_time=end_s,
                    status=SlotStatus.AVAILABLE,
                ))
                current = slot_end + buffer_td

        return slots
