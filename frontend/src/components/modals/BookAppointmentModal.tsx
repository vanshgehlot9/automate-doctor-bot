"use client";

import { useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getDoctors, getPatients, getAvailableSlots, createAppointment } from "@/lib/api";
import { useAuth } from "@/providers/AuthProvider";
import { Loader2, Calendar, Clock, User as UserIcon } from "lucide-react";
import { toast } from "sonner";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export function BookAppointmentModal() {
  const [open, setOpen] = useState(false);
  const { userProfile } = useAuth();
  const queryClient = useQueryClient();
  
  const [step, setStep] = useState(1);
  const [doctorId, setDoctorId] = useState<string>("");
  const [date, setDate] = useState<string>("");
  const [selectedSlot, setSelectedSlot] = useState<any>(null);
  
  const [patientId, setPatientId] = useState<string>("");
  const [reason, setReason] = useState<string>("");

  const { data: doctors } = useQuery({
    queryKey: ["doctors"],
    queryFn: getDoctors
  });

  const { data: patients } = useQuery({
    queryKey: ["patients"],
    queryFn: getPatients
  });

  const { data: slots, isLoading: loadingSlots } = useQuery({
    queryKey: ["slots", doctorId, date],
    queryFn: () => getAvailableSlots(doctorId, date, userProfile?.tenantId),
    enabled: !!doctorId && !!date
  });

  const bookMutation = useMutation({
    mutationFn: createAppointment,
    onSuccess: () => {
      toast.success("Appointment Confirmed!");
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
      setOpen(false);
      resetState();
    },
    onError: (err: any) => {
      // Handle the 409 Conflict if race condition occurred
      if (err.response?.status === 409) {
        toast.error("Sorry, this slot was just booked by someone else! Please choose another time.");
        // Refetch slots immediately
        queryClient.invalidateQueries({ queryKey: ["slots", doctorId, date] });
        setStep(2); // Send back to slot selection
      } else {
        toast.error(err.message || "Failed to book appointment");
      }
    }
  });

  const resetState = () => {
    setStep(1);
    setDoctorId("");
    setDate("");
    setSelectedSlot(null);
    setPatientId("");
    setReason("");
  };

  const handleBook = () => {
    if (!selectedSlot || !patientId) return;
    
    bookMutation.mutate({
      tenant_id: userProfile?.tenantId,
      doctor_id: doctorId,
      patient_id: patientId,
      appointment_date: date,
      appointment_time: selectedSlot.start_time,
      reason: reason || "General Consultation",
      status: "pending" as any // Initial status
    });
  };

  return (
    <Dialog open={open} onOpenChange={(val) => {
      setOpen(val);
      if (!val) resetState();
    }}>
      <DialogTrigger 
        render={
          <Button className="gap-2 bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm" />
        }
      >
        <Calendar className="w-4 h-4" /> Book Appointment
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Book New Appointment</DialogTitle>
          <DialogDescription>
            {step === 1 && "Select a doctor and date to view available slots."}
            {step === 2 && "Select an available time slot."}
            {step === 3 && "Select the patient and confirm booking."}
          </DialogDescription>
        </DialogHeader>

        {step === 1 && (
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Select Doctor</Label>
              <Select value={doctorId} onValueChange={(v) => setDoctorId(v || "")}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose a doctor" />
                </SelectTrigger>
                <SelectContent>
                  {doctors?.map(doc => (
                    <SelectItem key={doc.id} value={doc.id}>
                      Dr. {doc.name} - {doc.specialization}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>Select Date</Label>
              <Input type="date" value={date} onChange={e => setDate(e.target.value)} min={new Date().toISOString().split("T")[0]} />
            </div>

            <Button className="w-full" disabled={!doctorId || !date} onClick={() => setStep(2)}>
              View Available Slots
            </Button>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4 py-4">
            <div className="flex items-center gap-2 text-sm font-medium text-primary bg-primary/10 p-3 rounded-md">
              <Calendar className="w-4 h-4" /> 
              {new Date(date).toLocaleDateString()} with Dr. {doctors?.find(d => d.id === doctorId)?.name}
            </div>

            <div className="space-y-2">
              <Label>Available Slots</Label>
              {loadingSlots ? (
                <div className="py-8 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
              ) : slots && slots.length > 0 ? (
                <div className="grid grid-cols-3 gap-2 max-h-60 overflow-y-auto p-1">
                  {slots.map((slot: any) => (
                    <button
                      key={slot.start_time}
                      onClick={() => setSelectedSlot(slot)}
                      className={`py-2 px-3 text-sm rounded-md border font-medium transition-all
                        ${selectedSlot?.start_time === slot.start_time 
                          ? 'bg-primary text-primary-foreground border-primary shadow-md scale-105' 
                          : 'bg-card text-foreground hover:bg-primary/5 hover:border-primary/50'
                        }`}
                    >
                      {slot.start_time}
                    </button>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground bg-muted/50 rounded-lg border border-dashed">
                  <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No slots available on this date.</p>
                  <p className="text-xs mt-1">The doctor might be on leave or fully booked.</p>
                </div>
              )}
            </div>

            <div className="flex justify-between mt-6">
              <Button variant="outline" onClick={() => setStep(1)}>Back</Button>
              <Button disabled={!selectedSlot} onClick={() => setStep(3)}>Next Step</Button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4 py-4">
            <div className="flex items-center justify-between text-sm bg-muted/50 p-3 rounded-md border">
              <div>
                <p className="font-semibold">{new Date(date).toLocaleDateString()}</p>
                <p className="text-muted-foreground text-xs">{selectedSlot?.start_time} - {selectedSlot?.end_time}</p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setStep(2)}>Change Time</Button>
            </div>

            <div className="space-y-2">
              <Label>Select Patient</Label>
              <Select value={patientId} onValueChange={(v) => setPatientId(v || "")}>
                <SelectTrigger>
                  <SelectValue placeholder="Search or select patient" />
                </SelectTrigger>
                <SelectContent>
                  {patients?.map(p => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.name} ({p.phone})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Reason for Visit</Label>
              <Input 
                placeholder="e.g. Fever, Follow-up" 
                value={reason} 
                onChange={e => setReason(e.target.value)} 
              />
            </div>

            <div className="flex justify-between mt-6 pt-4 border-t">
              <Button variant="outline" onClick={() => setStep(2)}>Back</Button>
              <Button 
                onClick={handleBook} 
                disabled={!patientId || bookMutation.isPending}
                className="gap-2"
              >
                {bookMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                Confirm Booking
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
