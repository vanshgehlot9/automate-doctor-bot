"use client";

import { useState, useMemo } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Loader2, Search, Filter, Phone, FileText, CheckCircle2, Clock, CalendarX, Plus, Stethoscope, Navigation, Pill } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { getAppointments, getPatients } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { UploadPrescriptionModal } from "@/components/modals/UploadPrescriptionModal";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
};

const itemVariants = {
  hidden: { y: 20, opacity: 0 },
  show: { y: 0, opacity: 1, transition: { type: "spring" as const, stiffness: 300, damping: 24 } }
};

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

  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const sortedAppointments = useMemo(() => {
    let filtered = appointments || [];

    if (searchQuery) {
      const lowerQuery = searchQuery.toLowerCase();
      filtered = filtered.filter(appt => {
        const patient = patients?.find(p => p.id === appt.patient_id);
        return patient?.name.toLowerCase().includes(lowerQuery) || 
               patient?.phone?.includes(lowerQuery) ||
               appt.reason?.toLowerCase().includes(lowerQuery);
      });
    }

    if (statusFilter !== "all") {
      filtered = filtered.filter(appt => appt.status === statusFilter);
    }

    return filtered.slice().sort((a, b) => {
      const dateA = new Date(`${a.appointment_date}T${a.appointment_time}`);
      const dateB = new Date(`${b.appointment_date}T${b.appointment_time}`);
      return dateA.getTime() - dateB.getTime();
    });
  }, [appointments, patients, searchQuery, statusFilter]);

  const today = new Date().toDateString();
  const todaysAppts = appointments?.filter(a => new Date(a.appointment_date).toDateString() === today) || [];
  const completedToday = todaysAppts.filter(a => a.status === 'completed').length;
  const pendingToday = todaysAppts.filter(a => a.status === 'scheduled').length;
  const nextAppt = todaysAppts.filter(a => a.status === 'scheduled')
    .sort((a, b) => a.appointment_time.localeCompare(b.appointment_time))[0];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed': return <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 border-none font-medium">Completed</Badge>;
      case 'scheduled': return <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-100 border-none font-medium">Scheduled</Badge>;
      case 'cancelled': return <Badge className="bg-rose-100 text-rose-700 hover:bg-rose-100 border-none font-medium">Cancelled</Badge>;
      default: return <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100 border-none font-medium capitalize">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-8 pb-20 md:pb-10 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex justify-end gap-4">
        <div className="flex gap-3">
           <Button variant="outline" className="border-slate-200 shadow-sm hidden sm:flex">
             <CalendarX className="w-4 h-4 mr-2 text-slate-500" />
             Sync Calendar
           </Button>
           <Button className="bg-blue-600 hover:bg-blue-700 text-white shadow-sm hidden sm:flex">
             <Plus className="w-4 h-4 mr-2" />
             Book Appointment
           </Button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="border shadow-sm bg-white dark:bg-slate-900">
          <CardContent className="p-4 md:p-5 flex items-center gap-4">
             <div className="w-10 h-10 rounded-full bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 dark:text-blue-400">
                <Clock className="w-5 h-5" />
             </div>
             <div>
               <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Today</p>
               <h4 className="text-xl font-bold text-slate-900 dark:text-white">{todaysAppts.length}</h4>
             </div>
          </CardContent>
        </Card>
        <Card className="border shadow-sm bg-white dark:bg-slate-900">
          <CardContent className="p-4 md:p-5 flex items-center gap-4">
             <div className="w-10 h-10 rounded-full bg-amber-50 dark:bg-amber-900/30 flex items-center justify-center text-amber-600 dark:text-amber-400">
                <Loader2 className="w-5 h-5" />
             </div>
             <div>
               <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Pending</p>
               <h4 className="text-xl font-bold text-slate-900 dark:text-white">{pendingToday}</h4>
             </div>
          </CardContent>
        </Card>
        <Card className="border shadow-sm bg-white dark:bg-slate-900">
          <CardContent className="p-4 md:p-5 flex items-center gap-4">
             <div className="w-10 h-10 rounded-full bg-emerald-50 dark:bg-emerald-900/30 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="w-5 h-5" />
             </div>
             <div>
               <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Completed</p>
               <h4 className="text-xl font-bold text-slate-900 dark:text-white">{completedToday}</h4>
             </div>
          </CardContent>
        </Card>
        <Card className="border shadow-sm bg-white dark:bg-slate-900">
          <CardContent className="p-4 md:p-5 flex items-center gap-4">
             <div className="w-10 h-10 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-400">
                <Navigation className="w-5 h-5" />
             </div>
             <div className="overflow-hidden">
               <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Next Appt</p>
               <h4 className="text-lg font-bold text-slate-900 dark:text-white truncate">
                 {nextAppt ? nextAppt.appointment_time : '--:--'}
               </h4>
             </div>
          </CardContent>
        </Card>
      </div>

      {/* Search & Filters */}
      <div className="flex flex-col sm:flex-row gap-4 items-center bg-white dark:bg-slate-900 p-2 rounded-2xl border shadow-sm">
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input 
            placeholder="Search patients by name or phone..." 
            className="pl-9 border-none bg-transparent shadow-none focus-visible:ring-0 focus-visible:ring-offset-0"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="h-8 w-px bg-slate-200 dark:bg-slate-800 hidden sm:block"></div>
        <div className="flex items-center gap-2 w-full sm:w-auto px-2 pb-2 sm:pb-0">
          <Filter className="w-4 h-4 text-slate-400 hidden sm:block" />
          <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v || "all")}>
            <SelectTrigger className="w-full sm:w-[150px] border-none shadow-none bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors rounded-xl">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="scheduled">Scheduled</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Timeline */}
      <div className="relative">
        {/* Vertical line for desktop */}
        <div className="hidden md:block absolute left-[88px] top-4 bottom-4 w-px bg-slate-200 dark:bg-slate-800 z-0"></div>

        {isLoading ? (
          <div className="py-20 flex flex-col items-center justify-center space-y-4">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
            <p className="text-slate-500 font-medium">Loading appointments...</p>
          </div>
        ) : sortedAppointments.length === 0 ? (
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="py-16 px-6 text-center border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-3xl bg-slate-50 dark:bg-slate-900/50 mt-4"
          >
            <div className="w-20 h-20 bg-white dark:bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-6 shadow-sm border border-slate-100 dark:border-slate-700">
               <CalendarX className="w-10 h-10 text-slate-400" />
            </div>
            <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">No appointments found</h3>
            <p className="text-slate-500 max-w-sm mx-auto mb-8">
              {searchQuery || statusFilter !== 'all' 
                ? "We couldn't find any appointments matching your filters. Try adjusting your search criteria."
                : "Enjoy your free schedule or create a new appointment."}
            </p>
            <div className="flex items-center justify-center gap-4 flex-col sm:flex-row">
               <Button className="bg-blue-600 hover:bg-blue-700 text-white shadow-sm rounded-full px-6 w-full sm:w-auto">
                 <Plus className="w-4 h-4 mr-2" />
                 Book Appointment
               </Button>
               <Button variant="outline" className="rounded-full px-6 border-slate-200 shadow-sm w-full sm:w-auto">
                 Sync Calendar
               </Button>
            </div>
          </motion.div>
        ) : (
          <motion.div 
            variants={containerVariants}
            initial="hidden"
            animate="show"
            className="space-y-6 pt-4"
          >
            <AnimatePresence>
              {sortedAppointments.map((appt) => {
                const patient = patients?.find(p => p.id === appt.patient_id);
                const isPast = new Date(`${appt.appointment_date}T${appt.appointment_time}`).getTime() < new Date().getTime();
                const isToday = new Date(appt.appointment_date).toDateString() === new Date().toDateString();

                return (
                  <motion.div 
                    key={appt.id} 
                    variants={itemVariants}
                    layout
                    className="flex flex-col md:flex-row relative z-10"
                  >
                    {/* Time Column (Desktop) */}
                    <div className="hidden md:flex flex-col items-end pr-8 pt-6 w-32 shrink-0">
                      <span className={`text-sm font-bold ${isPast && appt.status !== 'completed' ? 'text-rose-500' : 'text-slate-900 dark:text-white'}`}>
                        {appt.appointment_time}
                      </span>
                      <span className="text-xs text-slate-500 mt-1">
                        {isToday ? 'Today' : new Date(appt.appointment_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                      </span>
                    </div>

                    {/* Timeline Dot (Desktop) */}
                    <div className="hidden md:flex flex-col items-center pt-6 pr-8">
                      <div className={`w-3 h-3 rounded-full ring-4 ring-slate-50 dark:ring-slate-950 z-10 ${
                        appt.status === 'completed' ? 'bg-emerald-500' : 
                        appt.status === 'scheduled' ? 'bg-blue-500' : 'bg-slate-300'
                      }`} />
                    </div>

                    {/* Card */}
                    <Card className="flex-1 border-slate-200/60 dark:border-slate-800 shadow-sm hover:shadow-md transition-all bg-white dark:bg-slate-900 overflow-hidden group rounded-[20px] flex flex-col hover:border-blue-300 dark:hover:border-blue-700">
                      <CardContent className="p-0 flex-1 flex flex-col">
                        
                        {/* Top Profile Section */}
                        <div className="p-4 sm:p-5 flex gap-4">
                          <Avatar className="w-12 h-12 sm:w-14 sm:h-14 border shadow-sm shrink-0">
                            <AvatarFallback className="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-bold text-sm sm:text-base">
                              {patient ? patient.name.substring(0, 2).toUpperCase() : 'PT'}
                            </AvatarFallback>
                          </Avatar>
                          <div className="flex-1 min-w-0">
                            <div className="flex justify-between items-start">
                              <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white truncate pr-2">
                                {patient ? patient.name : `Patient #${appt.patient_id.substring(0, 6)}`}
                              </h3>
                              <div className="shrink-0 scale-90 origin-top-right">
                                {getStatusBadge(appt.status)}
                              </div>
                            </div>
                            
                            <div className="flex flex-wrap items-center gap-1.5 mt-1 text-xs text-slate-500">
                               <span>{appt.patient_id.substring(0, 8)}</span>
                               {patient?.age && (
                                 <>
                                   <span className="w-1 h-1 rounded-full bg-slate-300"></span>
                                   <span>{patient.age} yrs</span>
                                 </>
                               )}
                               {patient?.gender && (
                                 <>
                                   <span className="w-1 h-1 rounded-full bg-slate-300"></span>
                                   <span className="capitalize">{patient.gender}</span>
                                 </>
                               )}
                            </div>
                            
                            {patient?.phone && (
                                <div className="flex items-center gap-1.5 mt-2 text-xs font-medium text-slate-600 dark:text-slate-400">
                                  <Phone className="w-3 h-3 text-slate-400" />
                                  {patient.phone}
                                </div>
                            )}
                          </div>
                        </div>

                        {/* Medical Context & Time */}
                        <div className="px-4 sm:px-5 pb-3">
                           <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3 border border-slate-100 dark:border-slate-800/80">
                             <div className="grid grid-cols-2 gap-3 text-xs">
                               <div>
                                 <p className="text-slate-400 mb-0.5 text-[10px] uppercase font-bold tracking-wider">Time & Date</p>
                                 <p className="font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1">
                                    <Clock className="w-3.5 h-3.5 text-blue-500" /> {appt.appointment_time}
                                 </p>
                                 <p className="text-[10px] text-slate-500 mt-0.5">
                                    {isToday ? 'Today' : new Date(appt.appointment_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                                 </p>
                               </div>
                               <div>
                                 <p className="text-slate-400 mb-0.5 text-[10px] uppercase font-bold tracking-wider">Reason</p>
                                 <p className="font-semibold text-slate-700 dark:text-slate-300 truncate">
                                   {appt.reason || 'Consultation'}
                                 </p>
                                 <p className="text-[10px] text-slate-500 truncate mt-0.5 flex items-center gap-1">
                                    <Stethoscope className="w-3 h-3 text-emerald-500"/> Checkup
                                 </p>
                               </div>
                             </div>
                           </div>
                        </div>

                        <div className="mt-auto"></div>

                        {/* Quick Actions Footer */}
                        <div className="border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 p-2 sm:p-3 flex items-center justify-between">
                          <div className="flex items-center gap-1">
                            <UploadPrescriptionModal 
                                appointmentId={appt.id} 
                                patientId={appt.patient_id} 
                                doctorId={appt.doctor_id} 
                                existingPrescriptionId={appt.prescription_id || undefined}
                                trigger={
                                  <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full text-slate-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-slate-800" title="Upload Prescription">
                                    <Pill className="w-4 h-4" />
                                  </Button>
                                }
                            />
                            <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full text-slate-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-slate-800" title="View Notes">
                                <FileText className="w-4 h-4" />
                            </Button>
                          </div>
                          
                          <div>
                            <Button size="sm" className={`h-8 rounded-full px-5 shadow-sm text-xs font-bold tracking-wide uppercase ${
                               appt.status === 'completed' 
                                ? 'bg-slate-200 text-slate-600 hover:bg-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700' 
                                : 'bg-blue-600 text-white hover:bg-blue-700'
                             }`}>
                               {appt.status === 'completed' ? 'View Details' : 'Start Consult'}
                            </Button>
                          </div>
                        </div>

                      </CardContent>
                    </Card>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </motion.div>
        )}
      </div>

      {/* Mobile FAB */}
      <Button 
        className="fixed bottom-6 right-6 md:hidden w-14 h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white shadow-[0_8px_30px_rgb(59,130,246,0.3)] z-50 flex items-center justify-center p-0"
      >
        <Plus className="w-6 h-6" />
      </Button>
    </div>
  );
}
