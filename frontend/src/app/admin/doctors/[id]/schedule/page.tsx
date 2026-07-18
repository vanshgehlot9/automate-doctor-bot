"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getDoctorSchedules, createDoctorSchedule, createDoctorHoliday } from "@/lib/api";
import { useAuth } from "@/providers/AuthProvider";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft, Clock, CalendarDays, Plus, Loader2 } from "lucide-react";
import { toast } from "sonner";

const DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function DoctorSchedulePage() {
  const params = useParams();
  const router = useRouter();
  const doctorId = params.id as string;
  const { userProfile } = useAuth();
  const queryClient = useQueryClient();

  const { data: schedules, isLoading } = useQuery({
    queryKey: ["schedules", doctorId],
    queryFn: () => getDoctorSchedules(doctorId)
  });

  const [activeDay, setActiveDay] = useState("0");
  const [formData, setFormData] = useState({
    start_time: "09:00",
    end_time: "17:00",
    slot_duration_minutes: 15,
    buffer_minutes: 5,
    break_start: "13:00",
    break_end: "14:00"
  });

  const [holidayData, setHolidayData] = useState({
    date: "",
    reason: "",
    type: "full_day"
  });

  useEffect(() => {
    if (schedules && schedules.length > 0) {
      const existing = schedules.find(s => s.day_of_week === parseInt(activeDay));
      if (existing) {
        setFormData({
          start_time: existing.start_time,
          end_time: existing.end_time,
          slot_duration_minutes: existing.slot_duration_minutes,
          buffer_minutes: existing.buffer_minutes,
          break_start: existing.break_start || "",
          break_end: existing.break_end || ""
        });
      } else {
        // Reset to default if no schedule exists for this day
        setFormData({
          start_time: "09:00",
          end_time: "17:00",
          slot_duration_minutes: 15,
          buffer_minutes: 5,
          break_start: "13:00",
          break_end: "14:00"
        });
      }
    }
  }, [schedules, activeDay]);

  const scheduleMutation = useMutation({
    mutationFn: createDoctorSchedule,
    onSuccess: () => {
      toast.success("Schedule updated successfully");
      queryClient.invalidateQueries({ queryKey: ["schedules", doctorId] });
    },
    onError: (err: any) => toast.error(err.message || "Failed to update schedule")
  });

  const holidayMutation = useMutation({
    mutationFn: createDoctorHoliday,
    onSuccess: () => {
      toast.success("Holiday added successfully");
      setHolidayData({ date: "", reason: "", type: "full_day" });
    },
    onError: (err: any) => toast.error(err.message || "Failed to add holiday")
  });

  const handleSaveSchedule = (e: React.FormEvent) => {
    e.preventDefault();
    scheduleMutation.mutate({
      doctor_id: doctorId,
      tenant_id: userProfile?.tenantId,
      day_of_week: parseInt(activeDay),
      ...formData,
      break_start: formData.break_start || null,
      break_end: formData.break_end || null
    });
  };

  const handleSaveHoliday = (e: React.FormEvent) => {
    e.preventDefault();
    holidayMutation.mutate({
      doctor_id: doctorId,
      tenant_id: userProfile?.tenantId,
      ...holidayData
    });
  };

  if (isLoading) return <div className="p-12 flex justify-center"><Loader2 className="animate-spin w-8 h-8 text-primary" /></div>;

  const currentDaySchedule = schedules?.find(s => s.day_of_week === parseInt(activeDay));

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Manage Schedule</h1>
          <p className="text-muted-foreground mt-1">Configure working hours and holidays.</p>
        </div>
      </div>

      <Tabs defaultValue="weekly" className="space-y-6">
        <TabsList>
          <TabsTrigger value="weekly" className="gap-2">
            <Clock className="w-4 h-4" /> Weekly Schedule
          </TabsTrigger>
          <TabsTrigger value="holidays" className="gap-2">
            <CalendarDays className="w-4 h-4" /> Holidays & Leaves
          </TabsTrigger>
        </TabsList>

        <TabsContent value="weekly">
          <Card>
            <CardHeader>
              <CardTitle>Working Hours</CardTitle>
              <CardDescription>Select a day to configure rules. If a day has no schedule, it acts as a weekly holiday.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-6">
                <div className="w-48 space-y-2 border-r pr-6">
                  {DAYS_OF_WEEK.map((day, index) => {
                    const hasSchedule = schedules?.some(s => s.day_of_week === index);
                    return (
                      <button
                        key={index}
                        onClick={() => {
                          setActiveDay(index.toString());
                          const existing = schedules?.find(s => s.day_of_week === index);
                          if (existing) {
                            setFormData({
                              start_time: existing.start_time,
                              end_time: existing.end_time,
                              slot_duration_minutes: existing.slot_duration_minutes,
                              buffer_minutes: existing.buffer_minutes,
                              break_start: existing.break_start || "",
                              break_end: existing.break_end || ""
                            });
                          }
                        }}
                        className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-colors flex justify-between items-center ${activeDay === index.toString() ? 'bg-primary text-primary-foreground' : 'hover:bg-muted text-muted-foreground'}`}
                      >
                        {day}
                        {hasSchedule && <span className="w-2 h-2 rounded-full bg-green-500"></span>}
                      </button>
                    )
                  })}
                </div>

                <div className="flex-1 max-w-2xl">
                  {currentDaySchedule && (
                    <div className="mb-6 p-4 bg-primary/5 border border-primary/20 rounded-lg">
                      <p className="text-sm font-medium text-primary">Currently Active Schedule for {DAYS_OF_WEEK[parseInt(activeDay)]}:</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {currentDaySchedule.start_time} - {currentDaySchedule.end_time} • {currentDaySchedule.slot_duration_minutes}m slots
                      </p>
                    </div>
                  )}

                  <form onSubmit={handleSaveSchedule} className="space-y-6">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Start Time</Label>
                        <Input type="time" required value={formData.start_time} onChange={e => setFormData({...formData, start_time: e.target.value})} />
                      </div>
                      <div className="space-y-2">
                        <Label>End Time</Label>
                        <Input type="time" required value={formData.end_time} onChange={e => setFormData({...formData, end_time: e.target.value})} />
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Slot Duration (mins)</Label>
                        <Input type="number" required value={formData.slot_duration_minutes} onChange={e => setFormData({...formData, slot_duration_minutes: parseInt(e.target.value)})} />
                      </div>
                      <div className="space-y-2">
                        <Label>Buffer (mins)</Label>
                        <Input type="number" required value={formData.buffer_minutes} onChange={e => setFormData({...formData, buffer_minutes: parseInt(e.target.value)})} />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 border-t pt-4">
                      <div className="space-y-2">
                        <Label>Lunch Break Start</Label>
                        <Input type="time" value={formData.break_start} onChange={e => setFormData({...formData, break_start: e.target.value})} />
                      </div>
                      <div className="space-y-2">
                        <Label>Lunch Break End</Label>
                        <Input type="time" value={formData.break_end} onChange={e => setFormData({...formData, break_end: e.target.value})} />
                      </div>
                    </div>

                    <Button type="submit" disabled={scheduleMutation.isPending}>
                      {scheduleMutation.isPending ? "Saving..." : `Save ${DAYS_OF_WEEK[parseInt(activeDay)]} Schedule`}
                    </Button>
                  </form>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="holidays">
          <Card>
            <CardHeader>
              <CardTitle>Add Holiday / Emergency Block</CardTitle>
              <CardDescription>Block off entire days or specific times to prevent bookings.</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSaveHoliday} className="max-w-xl space-y-4">
                <div className="space-y-2">
                  <Label>Date</Label>
                  <Input type="date" required value={holidayData.date} onChange={e => setHolidayData({...holidayData, date: e.target.value})} />
                </div>
                <div className="space-y-2">
                  <Label>Reason</Label>
                  <Input placeholder="e.g. Vacation, Emergency Surgery" required value={holidayData.reason} onChange={e => setHolidayData({...holidayData, reason: e.target.value})} />
                </div>
                <Button type="submit" disabled={holidayMutation.isPending} className="w-full gap-2">
                  <Plus className="w-4 h-4" /> Block Date
                </Button>
              </form>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
