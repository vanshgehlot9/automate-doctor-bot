"use client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity, Loader2 } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getAppointments, getPatients, updateAppointment } from "@/lib/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function WalkInQueuePage() {
  const queryClient = useQueryClient();
  const { data: appointments, isLoading: loadingAppts } = useQuery({ queryKey: ["appointments"], queryFn: getAppointments });
  const { data: patients, isLoading: loadingPatients } = useQuery({ queryKey: ["patients"], queryFn: getPatients });

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string, status: any }) => updateAppointment(id, { status }),
    onSuccess: () => {
      toast.success("Patient processed");
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
    }
  });

  const isLoading = loadingAppts || loadingPatients;
  const todaysAppointments = appointments?.filter(a => new Date(a.appointment_date).toDateString() === new Date().toDateString()) || [];
  const queue = todaysAppointments.filter(a => a.status === 'pending' || a.status === 'waiting').sort((a, b) => new Date(`1970-01-01T${a.appointment_time}`).getTime() - new Date(`1970-01-01T${b.appointment_time}`).getTime());

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Walk-in Queue</h1>
        <p className="text-muted-foreground mt-1">Manage patients currently waiting in the hospital.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-primary" />
            Today's Waiting List
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-muted-foreground" /></div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Patient</TableHead>
                  <TableHead>Current Status</TableHead>
                  <TableHead>Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {queue.length === 0 ? (
                  <TableRow><TableCell colSpan={4} className="text-center py-6 text-muted-foreground">No patients currently in queue.</TableCell></TableRow>
                ) : (
                  queue.map((appt) => {
                    const patient = patients?.find(p => p.id === appt.patient_id);
                    return (
                      <TableRow key={appt.id}>
                        <TableCell className="font-medium">{appt.appointment_time}</TableCell>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="font-medium">{patient ? patient.name : `Patient #${appt.patient_id.substring(0,6)}`}</span>
                            {patient?.phone && <span className="text-xs text-muted-foreground">{patient.phone}</span>}
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className="capitalize font-medium text-amber-600">{appt.status}</span>
                        </TableCell>
                        <TableCell>
                          <Button size="sm" onClick={() => updateStatus.mutate({ id: appt.id, status: 'in_progress' })}>Send to Doctor</Button>
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
