"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getPatients, getAppointments } from "@/lib/api";
import { useAuth } from "@/providers/AuthProvider";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { UploadPrescriptionModal } from "@/components/modals/UploadPrescriptionModal";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Users, Search, Plus, Phone, Mail, 
  Calendar, FileText, UserCircle, 
  AlertCircle, ChevronRight, Activity, Loader2, Pill, ActivitySquare, Stethoscope, Droplet
} from "lucide-react";

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 }
  }
};

const itemVariants = {
  hidden: { y: 15, opacity: 0 },
  show: { y: 0, opacity: 1, transition: { type: "spring" as const, stiffness: 300, damping: 24 } }
};

export default function DoctorPatientsPage() {
  const { userProfile } = useAuth();
  const router = useRouter();
  
  const { data: patients, isLoading: loadingPatients } = useQuery({
    queryKey: ["patients"],
    queryFn: getPatients
  });

  const { data: appointments, isLoading: loadingAppts } = useQuery({
    queryKey: ["appointments"],
    queryFn: getAppointments
  });

  const isLoading = loadingPatients || loadingAppts;

  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState("All");

  const filters = ["All", "Today's Patients", "New", "Follow-up", "Critical", "Chronic", "Recently Added"];

  // Metrics
  const today = new Date().toDateString();
  const todaysAppointments = appointments?.filter(a => new Date(a.appointment_date).toDateString() === today) || [];
  const followUps = appointments?.filter(a => a.status === 'scheduled' && a.reason?.toLowerCase().includes('follow')) || [];
  const newRegistrations = patients?.filter(p => {
    // Assuming created_at exists, if not, mock it or just use length of array roughly
    return true; 
  }).length || 0; // In a real app, filter by created_at > last 7 days

  const filteredPatients = useMemo(() => {
    let result = patients || [];

    // Search
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(p => 
        p.name.toLowerCase().includes(q) || 
        p.phone?.includes(q) || 
        p.id.toLowerCase().includes(q)
      );
    }

    // Filters
    if (activeFilter === "Today's Patients") {
      const todayPatientIds = todaysAppointments.map(a => a.patient_id);
      result = result.filter(p => todayPatientIds.includes(p.id));
    } else if (activeFilter === "Follow-up") {
      const followUpPatientIds = followUps.map(a => a.patient_id);
      result = result.filter(p => followUpPatientIds.includes(p.id));
    } else if (activeFilter === "Critical") {
      result = result.filter(p => p.allergies && p.allergies.length > 0);
    }
    // "New", "Chronic", "Recently Added" can be implemented with real schema fields when available.

    return result;
  }, [patients, appointments, searchQuery, activeFilter]);


  const getPatientMedicalAlerts = (patient: any) => {
    const alerts = [];
    if (patient.allergies && patient.allergies.length > 0) {
      alerts.push({ type: 'allergy', label: 'Allergy', icon: AlertCircle, color: 'text-amber-600 bg-amber-50 border-amber-200' });
    }
    // Mock conditions for demo based on blood group or other attributes if needed
    if (patient.blood_group === 'O-') {
      alerts.push({ type: 'critical', label: 'Universal Donor', icon: Droplet, color: 'text-rose-600 bg-rose-50 border-rose-200' });
    }
    return alerts;
  };

  const getPatientTimeline = (patientId: string) => {
    if (!appointments) return { lastVisit: null, nextAppt: null, diagnosis: null };
    
    const patientAppts = appointments.filter(a => a.patient_id === patientId);
    patientAppts.sort((a, b) => new Date(a.appointment_date).getTime() - new Date(b.appointment_date).getTime());
    
    const pastAppts = patientAppts.filter(a => new Date(a.appointment_date).getTime() < new Date().getTime());
    const futureAppts = patientAppts.filter(a => new Date(a.appointment_date).getTime() >= new Date().getTime() && a.status === 'scheduled');
    
    const lastVisit = pastAppts.length > 0 ? pastAppts[pastAppts.length - 1] : null;
    const nextAppt = futureAppts.length > 0 ? futureAppts[0] : null;

    return { lastVisit, nextAppt, diagnosis: lastVisit?.reason || null };
  };

  return (
    <div className="space-y-4 sm:space-y-6 pb-20 sm:pb-10 max-w-6xl mx-auto">
      
      {/* Search & Sticky Header area */}
      <div className="sticky top-0 z-30 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 pt-2 pb-4 -mx-4 px-4 sm:mx-0 sm:px-0 sm:pt-0 border-b sm:border-none sm:bg-transparent">
        <div className="flex flex-col sm:flex-row justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">Patients</h1>
            <p className="text-sm text-slate-500 hidden sm:block mt-1">Manage your patient directory and medical records.</p>
          </div>
          
          <div className="flex gap-2 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-72 md:w-80">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input 
                placeholder="Search name, phone, ID..." 
                className="pl-9 h-10 rounded-full bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <button 
                  onClick={() => setSearchQuery("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs font-medium"
                >
                  Clear
                </button>
              )}
            </div>
            <Button className="h-10 rounded-full shadow-sm bg-blue-600 hover:bg-blue-700 text-white hidden sm:flex shrink-0 px-5">
              <Plus className="w-4 h-4 mr-2" />
              Add Patient
            </Button>
          </div>
        </div>

        {/* Scrollable Filter Chips */}
        <div className="flex overflow-x-auto hide-scrollbar gap-2 mt-4 pb-1 sm:pb-0">
          {filters.map(filter => (
            <button
              key={filter}
              onClick={() => setActiveFilter(filter)}
              className={`whitespace-nowrap px-4 py-1.5 rounded-full text-xs sm:text-sm font-medium transition-colors border shadow-sm ${
                activeFilter === filter 
                  ? "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800" 
                  : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50 dark:bg-slate-900 dark:text-slate-300 dark:border-slate-800 dark:hover:bg-slate-800"
              }`}
            >
              {filter}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Summary Cards - 2 Column Grid on Mobile */}
      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4"
      >
        <motion.div variants={itemVariants}>
          <Card className="rounded-[16px] sm:rounded-[20px] border shadow-sm bg-white dark:bg-slate-900">
            <CardContent className="p-3 sm:p-4 md:p-5 flex items-center gap-3">
              <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 dark:text-blue-400 shrink-0">
                <Users className="w-4 h-4 sm:w-5 sm:h-5" />
              </div>
              <div>
                <p className="text-[10px] sm:text-xs font-medium text-slate-500">Total Patients</p>
                <h4 className="text-lg sm:text-2xl font-bold text-slate-900 dark:text-white leading-none mt-0.5">
                  {patients?.length || 0}
                </h4>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Card className="rounded-[16px] sm:rounded-[20px] border shadow-sm bg-white dark:bg-slate-900">
            <CardContent className="p-3 sm:p-4 md:p-5 flex items-center gap-3">
              <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-emerald-50 dark:bg-emerald-900/30 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shrink-0">
                <Calendar className="w-4 h-4 sm:w-5 sm:h-5" />
              </div>
              <div>
                <p className="text-[10px] sm:text-xs font-medium text-slate-500">Today's Visits</p>
                <h4 className="text-lg sm:text-2xl font-bold text-slate-900 dark:text-white leading-none mt-0.5">
                  {todaysAppointments.length}
                </h4>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Card className="rounded-[16px] sm:rounded-[20px] border shadow-sm bg-white dark:bg-slate-900">
            <CardContent className="p-3 sm:p-4 md:p-5 flex items-center gap-3">
              <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-amber-50 dark:bg-amber-900/30 flex items-center justify-center text-amber-600 dark:text-amber-400 shrink-0">
                <ActivitySquare className="w-4 h-4 sm:w-5 sm:h-5" />
              </div>
              <div>
                <p className="text-[10px] sm:text-xs font-medium text-slate-500">Follow-ups</p>
                <h4 className="text-lg sm:text-2xl font-bold text-slate-900 dark:text-white leading-none mt-0.5">
                  {followUps.length}
                </h4>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Card className="rounded-[16px] sm:rounded-[20px] border shadow-sm bg-white dark:bg-slate-900">
            <CardContent className="p-3 sm:p-4 md:p-5 flex items-center gap-3">
              <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-purple-50 dark:bg-purple-900/30 flex items-center justify-center text-purple-600 dark:text-purple-400 shrink-0">
                <Plus className="w-4 h-4 sm:w-5 sm:h-5" />
              </div>
              <div>
                <p className="text-[10px] sm:text-xs font-medium text-slate-500">New (This Mth)</p>
                <h4 className="text-lg sm:text-2xl font-bold text-slate-900 dark:text-white leading-none mt-0.5">
                  {newRegistrations}
                </h4>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>

      {/* Main List Area */}
      <div className="relative min-h-[400px]">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-64 space-y-4">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
            <p className="text-sm text-slate-500 font-medium">Loading patient directory...</p>
          </div>
        ) : filteredPatients.length === 0 ? (
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex flex-col items-center justify-center py-20 px-4 text-center border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-3xl bg-slate-50/50 dark:bg-slate-900/30 mt-6"
          >
            <div className="w-20 h-20 bg-white dark:bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-6 shadow-sm border border-slate-100 dark:border-slate-700">
               <Users className="w-10 h-10 text-slate-400" />
            </div>
            <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">No patients found</h3>
            <p className="text-slate-500 max-w-sm mx-auto mb-8 text-sm">
              {searchQuery || activeFilter !== "All"
                ? "We couldn't find any patients matching your current filters and search query."
                : "Your patient directory is currently empty. Start by adding a new patient."}
            </p>
            <Button className="h-11 rounded-full px-8 shadow-md bg-blue-600 hover:bg-blue-700 text-white">
              <Plus className="w-4 h-4 mr-2" />
              Register New Patient
            </Button>
          </motion.div>
        ) : (
          <motion.div 
            variants={containerVariants}
            initial="hidden"
            animate="show"
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
          >
            <AnimatePresence>
              {filteredPatients.map(patient => {
                const alerts = getPatientMedicalAlerts(patient);
                const timeline = getPatientTimeline(patient.id);
                const isNew = true; // In real app, calculate based on created_at

                return (
                  <motion.div key={patient.id} variants={itemVariants} layout className="h-full">
                      <Card className="rounded-[20px] border-slate-200/60 dark:border-slate-800 shadow-sm hover:shadow-md transition-all duration-200 bg-white dark:bg-slate-900 overflow-hidden group h-full flex flex-col hover:border-blue-300 dark:hover:border-blue-700">
                      <CardContent className="p-0 flex-1 flex flex-col">
                        
                        {/* Top Profile Section */}
                        <div 
                          className="p-4 sm:p-5 flex gap-4 cursor-pointer" 
                          onClick={() => router.push(`/doctor/patients/${patient.id}`)}
                        >
                          <Avatar className="w-12 h-12 sm:w-14 sm:h-14 border shadow-sm shrink-0">
                            <AvatarFallback className="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-bold text-sm sm:text-base">
                              {patient.name.substring(0, 2).toUpperCase()}
                            </AvatarFallback>
                          </Avatar>
                          <div className="flex-1 min-w-0">
                            <div className="flex justify-between items-start">
                              <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white truncate">
                                {patient.name}
                              </h3>
                              {isNew && (
                                <Badge className="bg-blue-50 text-blue-700 hover:bg-blue-50 border-none px-1.5 py-0 text-[10px] uppercase font-bold shrink-0 ml-2">
                                  New
                                </Badge>
                              )}
                            </div>
                            
                            <div className="flex flex-wrap items-center gap-1.5 mt-1 text-xs text-slate-500">
                              <span>{patient.id.substring(0, 8)}</span>
                              <span className="w-1 h-1 rounded-full bg-slate-300"></span>
                              <span>{patient.age || '--'} yrs</span>
                              {patient.gender && (
                                <>
                                  <span className="w-1 h-1 rounded-full bg-slate-300"></span>
                                  <span className="capitalize">{patient.gender}</span>
                                </>
                              )}
                            </div>

                            {patient.phone && (
                              <div className="flex items-center gap-1.5 mt-2 text-xs font-medium text-slate-600 dark:text-slate-400">
                                <Phone className="w-3 h-3 text-slate-400" />
                                {patient.phone}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Medical Alerts & Context */}
                        <div className="px-4 sm:px-5 pb-3">
                          {/* Alerts */}
                          <div className="flex flex-wrap gap-1.5 mb-3">
                            {alerts.map((alert, i) => {
                              const Icon = alert.icon;
                              return (
                                <Badge key={i} variant="outline" className={`text-[10px] px-1.5 py-0 h-5 flex items-center gap-1 ${alert.color}`}>
                                  <Icon className="w-2.5 h-2.5" />
                                  {alert.label}
                                </Badge>
                              )
                            })}
                            {patient.blood_group && (
                              <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-5 text-slate-600 border-slate-200 bg-slate-50 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700">
                                🩸 {patient.blood_group}
                              </Badge>
                            )}
                          </div>

                          {/* Timeline Preview */}
                          <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3 border border-slate-100 dark:border-slate-800/80">
                            <div className="grid grid-cols-2 gap-3 text-xs">
                              <div>
                                <p className="text-slate-400 mb-0.5 text-[10px] uppercase font-bold tracking-wider">Last Visit</p>
                                <p className="font-semibold text-slate-700 dark:text-slate-300">
                                  {timeline.lastVisit ? new Date(timeline.lastVisit.appointment_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : '--'}
                                </p>
                                {timeline.diagnosis && (
                                  <p className="text-[10px] text-slate-500 truncate mt-0.5">{timeline.diagnosis}</p>
                                )}
                              </div>
                              <div>
                                <p className="text-slate-400 mb-0.5 text-[10px] uppercase font-bold tracking-wider">Next Appt</p>
                                <p className="font-semibold text-slate-700 dark:text-slate-300">
                                  {timeline.nextAppt ? new Date(timeline.nextAppt.appointment_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : 'None'}
                                </p>
                                {timeline.nextAppt && (
                                  <p className="text-[10px] text-blue-600 dark:text-blue-400 font-medium truncate mt-0.5">{timeline.nextAppt.appointment_time}</p>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>

                        <div className="mt-auto"></div>

                        {/* Quick Actions Footer */}
                        <div className="border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 p-2 sm:p-3 flex items-center justify-between">
                          <div className="flex items-center gap-1">
                            <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full text-slate-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-slate-800" title="View Profile" onClick={() => router.push(`/doctor/patients/${patient.id}`)}>
                              <UserCircle className="w-4 h-4" />
                            </Button>
                            <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full text-slate-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-slate-800" title="Medical Records" onClick={() => router.push(`/doctor/patients/${patient.id}`)}>
                              <FileText className="w-4 h-4" />
                            </Button>
                            {/* Reusing UploadPrescriptionModal logic seamlessly as an icon button */}
                            <UploadPrescriptionModal 
                              patientId={patient.id} 
                              doctorId={userProfile?.id || ""}
                              trigger={
                                <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full text-slate-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-slate-800" title="Prescription">
                                  <Pill className="w-4 h-4" />
                                </Button>
                              }
                            />
                          </div>
                          
                          <div className="flex items-center gap-1">
                             <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full text-slate-500 hover:text-emerald-600 hover:bg-emerald-50 dark:hover:bg-slate-800" title="Call">
                              <Phone className="w-3.5 h-3.5" />
                            </Button>
                            <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full text-slate-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-slate-800" title="Message">
                              <Mail className="w-3.5 h-3.5" />
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
