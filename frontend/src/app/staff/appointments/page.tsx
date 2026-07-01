"use client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Calendar, Loader2 } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getAppointments, getPatients, updateAppointment } from "@/lib/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function StaffAppointmentsPage() {
  const queryClient = useQueryClient();
  const { data: appointments, isLoading: loadingAppts } = useQuery({ queryKey: ["appointments"], queryFn: getAppointments });
  const { data: patients, isLoading: loadingPatients } = useQuery({ queryKey: ["patients"], queryFn: getPatients });

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string, status: any }) => updateAppointment(id, { status }),
    onSuccess: () => {
      toast.success("Status updated");
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
    }
  });

  const isLoading = loadingAppts || loadingPatients;
  const sortedAppointments = appointments?.slice().sort((a, b) => new Date(`${b.appointment_date}T${b.appointment_time}`).getTime() - new Date(`${a.appointment_date}T${a.appointment_time}`).getTime()) || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Staff Appointments</h1>
        <p className="text-muted-foreground mt-1">Manage scheduled appointments for the hospital.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-primary" />
            All Appointments
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-muted-foreground" /></div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date & Time</TableHead>
                  <TableHead>Patient</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedAppointments.length === 0 ? (
                  <TableRow><TableCell colSpan={4} className="text-center py-6 text-muted-foreground">No appointments found.</TableCell></TableRow>
                ) : (
                  sortedAppointments.map((appt) => {
                    const patient = patients?.find(p => p.id === appt.patient_id);
                    return (
                      <TableRow key={appt.id}>
                        <TableCell className="font-medium whitespace-nowrap">{new Date(appt.appointment_date).toLocaleDateString()} at {appt.appointment_time}</TableCell>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="font-medium">{patient ? patient.name : `Patient #${appt.patient_id.substring(0,6)}`}</span>
                            {patient?.phone && <span className="text-xs text-muted-foreground">{patient.phone}</span>}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={appt.status === 'scheduled' ? 'default' : appt.status === 'completed' ? 'success' : 'secondary'}>
                            {appt.status.charAt(0).toUpperCase() + appt.status.slice(1)}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {appt.status === 'pending' || appt.status === 'scheduled' || appt.status === 'confirmed' ? (
                            <Button size="sm" onClick={() => updateStatus.mutate({ id: appt.id, status: 'waiting' })}>Mark Waiting</Button>
                          ) : appt.status === 'waiting' ? (
                            <Button size="sm" variant="outline" onClick={() => updateStatus.mutate({ id: appt.id, status: 'completed' })}>Complete</Button>
                          ) : <span className="text-muted-foreground text-xs">No actions</span>}
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
