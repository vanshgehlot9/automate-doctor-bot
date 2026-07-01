"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Calendar, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { getAppointments, getPatients } from "@/lib/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { UploadPrescriptionModal } from "@/components/modals/UploadPrescriptionModal";

export default function DoctorAppointmentsPage() {
  const { data: appointments, isLoading: loadingAppts } = useQuery({
    queryKey: ["appointments"],
    queryFn: getAppointments
  });

  const { data: patients, isLoading: loadingPatients } = useQuery({
    queryKey: ["patients"],
    queryFn: getPatients
  });

  const isLoading = loadingAppts || loadingPatients;

  // Sort appointments by date and time
  const sortedAppointments = appointments?.slice().sort((a, b) => {
    const dateA = new Date(`${a.appointment_date}T${a.appointment_time}`);
    const dateB = new Date(`${b.appointment_date}T${b.appointment_time}`);
    return dateA.getTime() - dateB.getTime();
  }) || [];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Appointments</h1>
          <p className="text-muted-foreground mt-1">Manage all your scheduled consultations.</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-primary" />
            Appointments Directory
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-muted-foreground" /></div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                <TableRow>
                  <TableHead>Date & Time</TableHead>
                  <TableHead>Patient</TableHead>
                  <TableHead>Reason</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Prescription</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedAppointments.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-6 text-muted-foreground">No appointments found.</TableCell>
                  </TableRow>
                ) : (
                  sortedAppointments.map((appt) => {
                    const patient = patients?.find(p => p.id === appt.patient_id);
                    return (
                      <TableRow key={appt.id}>
                        <TableCell className="font-medium whitespace-nowrap">
                          {new Date(appt.appointment_date).toLocaleDateString()} at {appt.appointment_time}
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="font-medium">{patient ? patient.name : `Patient #${appt.patient_id.substring(0,6)}`}</span>
                            {patient?.phone && <span className="text-xs text-muted-foreground">{patient.phone}</span>}
                          </div>
                        </TableCell>
                        <TableCell>{appt.reason || "General Consultation"}</TableCell>
                        <TableCell>
                          <Badge variant={
                            appt.status === 'scheduled' ? 'default' :
                            appt.status === 'completed' ? 'success' :
                            'secondary'
                          }>
                            {appt.status.charAt(0).toUpperCase() + appt.status.slice(1)}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <UploadPrescriptionModal 
                            appointmentId={appt.id} 
                            patientId={appt.patient_id} 
                            doctorId={appt.doctor_id} 
                            existingPrescriptionId={appt.prescription_id || undefined}
                          />
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
