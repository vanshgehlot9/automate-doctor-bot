"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAppointments, getLaboratoryTests, getPatients } from "@/lib/api";
import { useAuth } from "@/providers/AuthProvider";
import { WriteNoteModal } from "@/components/modals/WriteNoteModal";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { 
  Users, 
  Calendar, 
  Activity, 
  Microscope, 
  Loader2, 
  Clock, 
  ChevronRight, 
  Plus, 
  FileText,
  Stethoscope,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  MapPin
} from "lucide-react";
import { format } from "date-fns";
import { motion } from "framer-motion";
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip as RechartsTooltip, 
  ResponsiveContainer,
  BarChart,
  Bar
} from "recharts";

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

export default function DoctorDashboard() {
  const { userProfile } = useAuth();
  
  const { data: appointments, isLoading: loadingAppts } = useQuery({
    queryKey: ["appointments"],
    queryFn: getAppointments
  });

  const { data: labTests, isLoading: loadingLabs } = useQuery({
    queryKey: ["laboratoryTests"],
    queryFn: getLaboratoryTests
  });

  const { data: patients, isLoading: loadingPatients } = useQuery({
    queryKey: ["patients"],
    queryFn: getPatients
  });

  const isLoading = loadingAppts || loadingLabs || loadingPatients;

  // Derived Data
  const todaysAppointments = appointments?.filter(a => new Date(a.appointment_date).toDateString() === new Date().toDateString()) || [];
  
  const upcomingPatients = todaysAppointments.filter(a => a.status === 'scheduled')
    .sort((a, b) => a.appointment_time.localeCompare(b.appointment_time));

  const completedPatients = todaysAppointments.filter(a => a.status === 'completed');

  const unreadReports = labTests?.filter(t => t.status === 'pending' || t.status === 'completed' && !t.result_summary).length || 0;

  const pendingFollowUps = appointments?.filter(a => 
    a.status === 'scheduled' && a.reason?.toLowerCase().includes('follow')
  ).length || 0;

  // Queue calculations
  const totalQueue = upcomingPatients.length;
  const queueProgress = todaysAppointments.length > 0 
    ? (completedPatients.length / todaysAppointments.length) * 100 
    : 0;

  const nextAppointment = upcomingPatients.length > 0 ? upcomingPatients[0] : null;
  const nextPatient = nextAppointment ? patients?.find(p => p.id === nextAppointment.patient_id) : null;

  // Graph Data
  const chartData = useMemo(() => {
    if (!appointments) return [];
    const today = new Date().toDateString();
    const todaysAppts = appointments.filter(a => new Date(a.appointment_date).toDateString() === today);
    
    const hours = ['09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00'];
    return hours.map(hour => {
      const prefix = hour.split(':')[0];
      const count = todaysAppts.filter(a => a.appointment_time.startsWith(prefix)).length;
      return { time: hour, patients: count };
    });
  }, [appointments]);

  const weeklyData = useMemo(() => {
    if (!appointments) return [];
    const counts = [0, 0, 0, 0, 0, 0, 0];
    
    appointments.forEach(a => {
      const date = new Date(a.appointment_date);
      if (!isNaN(date.getTime())) {
        counts[date.getDay()]++;
      }
    });
    
    return [
      { day: 'Mon', visits: counts[1] },
      { day: 'Tue', visits: counts[2] },
      { day: 'Wed', visits: counts[3] },
      { day: 'Thu', visits: counts[4] },
      { day: 'Fri', visits: counts[5] },
      { day: 'Sat', visits: counts[6] },
      { day: 'Sun', visits: counts[0] },
    ];
  }, [appointments]);

  return (
    <div className="space-y-4 sm:space-y-6 pb-10">
      
      {/* Header Section */}
      <motion.div 
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-card p-4 sm:p-6 md:p-8 rounded-[20px] border shadow-sm"
      >
        <div>
          <h1 className="text-xl sm:text-2xl md:text-3xl font-bold tracking-tight text-foreground">
            Good Morning, <span className="text-primary">{userProfile?.name?.split(' ')[0] || 'Doctor'}</span>
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
            You have {upcomingPatients.length} appointments today.
          </p>
        </div>
        <div className="flex items-center gap-2 mt-1 sm:mt-0">
          <WriteNoteModal 
            appointments={appointments || []} 
            patients={patients || []} 
            trigger={
              <Button variant="outline" size="sm" className="h-9 sm:h-10 rounded-full shadow-sm hover:shadow-md transition-shadow text-xs px-3 sm:px-4">
                Write Note
              </Button>
            } 
          />
        </div>
      </motion.div>

      {/* KPI Cards - 2 Column Grid on Mobile */}
      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4"
      >
        {/* Appointments Card */}
        <motion.div variants={itemVariants}>
          <Card className="rounded-[16px] sm:rounded-[20px] border shadow-sm hover:shadow-md transition-all duration-300 bg-card overflow-hidden">
            <CardContent className="p-3 sm:p-4 md:p-5">
              <div className="flex items-center gap-2 sm:gap-3 mb-2">
                <div className="w-7 h-7 sm:w-9 sm:h-9 rounded-full bg-blue-50 dark:bg-blue-500/10 flex items-center justify-center text-blue-500 shrink-0">
                  <Calendar className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                </div>
                <p className="text-[11px] sm:text-xs md:text-sm font-semibold text-muted-foreground line-clamp-1">Appts</p>
              </div>
              <div className="flex items-end justify-between mt-1">
                <h3 className="text-xl sm:text-2xl font-bold text-foreground leading-none">
                  {loadingAppts ? <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /> : todaysAppointments.length}
                </h3>
                <span className="flex items-center text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 px-1.5 py-0.5 rounded-full text-[10px] font-medium leading-none">
                  <TrendingUp className="w-2.5 h-2.5 mr-0.5" />
                  +2
                </span>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Queue Card */}
        <motion.div variants={itemVariants}>
          <Card className="rounded-[16px] sm:rounded-[20px] border shadow-sm hover:shadow-md transition-all duration-300 bg-card overflow-hidden">
            <CardContent className="p-3 sm:p-4 md:p-5">
              <div className="flex items-center gap-2 sm:gap-3 mb-2">
                <div className="w-7 h-7 sm:w-9 sm:h-9 rounded-full bg-emerald-50 dark:bg-emerald-500/10 flex items-center justify-center text-emerald-500 shrink-0">
                  <Users className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                </div>
                <p className="text-[11px] sm:text-xs md:text-sm font-semibold text-muted-foreground line-clamp-1">Queue</p>
              </div>
              <div className="flex items-end justify-between mt-1">
                <h3 className="text-xl sm:text-2xl font-bold text-foreground leading-none">
                  {loadingAppts ? <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /> : totalQueue}
                </h3>
                <span className="text-[10px] font-medium text-muted-foreground">
                  {Math.round(queueProgress)}% done
                </span>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Reports Card */}
        <motion.div variants={itemVariants}>
          <Card className="rounded-[16px] sm:rounded-[20px] border shadow-sm hover:shadow-md transition-all duration-300 bg-card overflow-hidden">
            <CardContent className="p-3 sm:p-4 md:p-5">
              <div className="flex items-center gap-2 sm:gap-3 mb-2 relative">
                <div className="w-7 h-7 sm:w-9 sm:h-9 rounded-full bg-purple-50 dark:bg-purple-500/10 flex items-center justify-center text-purple-500 shrink-0">
                  <Microscope className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                </div>
                {unreadReports > 0 && (
                  <span className="absolute top-0 left-5 sm:left-7 w-2 h-2 sm:w-2.5 sm:h-2.5 bg-purple-500 rounded-full border-2 border-card"></span>
                )}
                <p className="text-[11px] sm:text-xs md:text-sm font-semibold text-muted-foreground line-clamp-1">Reports</p>
              </div>
              <div className="flex items-end justify-between mt-1">
                <h3 className="text-xl sm:text-2xl font-bold text-foreground leading-none">
                  {loadingLabs ? <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /> : unreadReports}
                </h3>
                {unreadReports > 0 && (
                  <span className="flex items-center text-amber-600 dark:text-amber-400 text-[10px] font-medium leading-none">
                    <AlertCircle className="w-2.5 h-2.5 mr-0.5" />
                    New
                  </span>
                )}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Follow-ups Card */}
        <motion.div variants={itemVariants}>
          <Card className="rounded-[16px] sm:rounded-[20px] border shadow-sm hover:shadow-md transition-all duration-300 bg-card overflow-hidden">
            <CardContent className="p-3 sm:p-4 md:p-5">
              <div className="flex items-center gap-2 sm:gap-3 mb-2">
                <div className="w-7 h-7 sm:w-9 sm:h-9 rounded-full bg-amber-50 dark:bg-amber-500/10 flex items-center justify-center text-amber-500 shrink-0">
                  <Activity className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                </div>
                <p className="text-[11px] sm:text-xs md:text-sm font-semibold text-muted-foreground line-clamp-1">Follow-ups</p>
              </div>
              <div className="flex items-end justify-between mt-1">
                <h3 className="text-xl sm:text-2xl font-bold text-foreground leading-none">
                  {loadingAppts ? <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /> : pendingFollowUps}
                </h3>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        
        {/* Right Column (Moved up on mobile for Next Patient context) - AI Assistant & Weekly Stats */}
        <div className="space-y-4 sm:space-y-6 lg:col-start-3 lg:col-span-1">
          {/* Next Patient Context - Professional UI */}
          <Card className="rounded-[20px] border shadow-sm bg-muted/10">
            <CardHeader className="pb-3 px-4 sm:px-6 pt-4 sm:pt-6">
              <CardTitle className="flex items-center gap-2 text-primary text-sm sm:text-lg">
                <div className="p-1 sm:p-1.5 rounded-lg bg-primary/10 text-primary">
                  <Activity className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                </div>
                Clinical Assistant
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 sm:px-6 pb-4 sm:pb-6">
              {isLoading ? (
                <div className="py-6 flex justify-center"><Loader2 className="animate-spin text-primary w-5 h-5" /></div>
              ) : nextPatient ? (
                <div className="space-y-3 sm:space-y-4">
                  <div className="p-3 sm:p-4 bg-background rounded-xl border shadow-sm">
                    <div className="flex items-center justify-between mb-2 sm:mb-3">
                      <span className="text-[10px] sm:text-xs font-semibold text-primary uppercase tracking-wider">Next Up</span>
                      <span className="text-[10px] sm:text-xs font-medium bg-muted px-2 py-0.5 sm:py-1 rounded-md">{nextAppointment?.appointment_time}</span>
                    </div>
                    <div className="flex items-center gap-3 mb-2 sm:mb-3">
                      <Avatar className="w-10 h-10 sm:w-12 sm:h-12 border-2 border-background shadow-sm">
                        <AvatarFallback className="bg-primary text-primary-foreground text-sm sm:text-lg">
                          {nextPatient.name.substring(0, 2).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <h4 className="font-bold text-sm sm:text-base text-foreground line-clamp-1">{nextPatient.name}</h4>
                        <p className="text-xs sm:text-sm text-muted-foreground">{nextPatient.age || 'Unknown'} yrs • {nextPatient.gender || 'Unknown'}</p>
                      </div>
                    </div>
                    
                    <div className="space-y-2 mt-3 sm:mt-4 pt-2 sm:pt-3 border-t">
                      <div className="flex flex-wrap gap-1.5 sm:gap-2">
                        <Badge variant="secondary" className="bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 hover:bg-blue-100 border-blue-200 dark:border-blue-800 text-[10px] sm:text-xs">
                          {nextAppointment?.reason || 'Consultation'}
                        </Badge>
                        {nextPatient.blood_group && (
                          <Badge variant="outline" className="text-rose-500 border-rose-200 dark:border-rose-900/50 text-[10px] sm:text-xs">
                            {nextPatient.blood_group}
                          </Badge>
                        )}
                      </div>
                      
                      {nextAppointment?.notes && (
                        <p className="text-xs sm:text-sm text-muted-foreground mt-2 italic bg-muted/50 p-2 rounded-lg border">
                          "{nextAppointment.notes}"
                        </p>
                      )}
                    </div>
                  </div>

                  {nextPatient.allergies && nextPatient.allergies.length > 0 && (
                    <div className="p-2 sm:p-3 bg-red-50 dark:bg-red-950/30 rounded-xl border border-red-100 dark:border-red-900/50 flex items-start gap-2 shadow-sm">
                      <AlertCircle className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-red-500 mt-0.5 shrink-0" />
                      <div>
                        <span className="text-[10px] sm:text-xs font-semibold text-red-700 dark:text-red-400 uppercase">Allergies</span>
                        <p className="text-[11px] sm:text-sm text-red-600 dark:text-red-300 font-medium leading-tight mt-0.5">
                          {nextPatient.allergies.join(", ")}
                        </p>
                      </div>
                    </div>
                  )}

                  <Button className="w-full rounded-xl py-4 sm:py-6 h-auto shadow-md hover:shadow-lg transition-all bg-foreground hover:bg-foreground/90 text-background text-xs sm:text-sm font-medium">
                    Generate AI Summary
                  </Button>
                </div>
              ) : (
                <div className="p-6 sm:p-8 text-center bg-background rounded-xl border border-dashed">
                  <div className="w-10 h-10 sm:w-12 sm:h-12 bg-muted rounded-full flex items-center justify-center mx-auto mb-2 sm:mb-3">
                    <CheckCircle2 className="w-5 h-5 sm:w-6 sm:h-6 text-muted-foreground" />
                  </div>
                  <p className="text-xs sm:text-sm text-muted-foreground font-medium">Queue is empty</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Weekly Overview (Hidden on very small screens to save space) */}
          <Card className="rounded-[20px] border-border/50 shadow-sm hidden sm:block">
            <CardHeader className="pb-2">
              <CardTitle className="text-md">Weekly Overview</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[180px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={weeklyData} margin={{ top: 0, right: 0, left: -25, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                    <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} dy={5} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                    <RechartsTooltip 
                      cursor={{ fill: 'hsl(var(--muted)/0.5)' }}
                      contentStyle={{ borderRadius: '8px', border: '1px solid hsl(var(--border))', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', fontSize: '12px' }}
                    />
                    <Bar dataKey="visits" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} maxBarSize={40} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Left Column - Patient Flow Chart & Timeline */}
        <div className="lg:col-span-2 space-y-4 sm:space-y-6 lg:row-start-1">
          
          {/* Timeline Section */}
          <Card className="rounded-[20px] border-border/50 shadow-sm overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between border-b bg-muted/10 pb-3 sm:pb-4 px-4 sm:px-6 pt-4 sm:pt-6">
              <div>
                <CardTitle className="text-base sm:text-lg">Upcoming Appointments</CardTitle>
              </div>
              <Button variant="ghost" size="sm" className="text-primary rounded-full hover:bg-primary/10 h-8 text-xs sm:text-sm px-2 sm:px-3">
                View All <ChevronRight className="w-3.5 h-3.5 sm:w-4 sm:h-4 ml-0.5 sm:ml-1" />
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <div className="flex flex-col">
                {isLoading ? (
                  <div className="p-8 sm:p-12 flex flex-col items-center justify-center text-muted-foreground">
                    <Loader2 className="w-6 h-6 sm:w-8 sm:h-8 animate-spin mb-3 sm:mb-4 text-primary" />
                    <p className="text-sm">Loading schedule...</p>
                  </div>
                ) : upcomingPatients.length === 0 ? (
                  <div className="p-8 sm:p-12 flex flex-col items-center justify-center text-center">
                    <div className="w-12 h-12 sm:w-16 sm:h-16 bg-muted rounded-full flex items-center justify-center mb-3 sm:mb-4">
                      <Stethoscope className="w-6 h-6 sm:w-8 sm:h-8 text-muted-foreground/50" />
                    </div>
                    <h3 className="text-base sm:text-lg font-medium text-foreground">No more appointments</h3>
                    <p className="text-xs sm:text-sm text-muted-foreground max-w-[250px] mt-1">
                      You have cleared your queue for today. Time for a well-deserved break!
                    </p>
                  </div>
                ) : (
                  <div className="divide-y divide-border/50">
                    {upcomingPatients.map((appt, index) => {
                      const patient = patients?.find(p => p.id === appt.patient_id);
                      const isNext = index === 0;
                      
                      return (
                        <div key={appt.id} className={`p-3 sm:p-6 transition-colors hover:bg-muted/30 flex flex-col sm:flex-row gap-3 sm:gap-4 sm:items-center justify-between group ${isNext ? 'bg-primary/5 hover:bg-primary/5' : ''}`}>
                          <div className="flex items-start sm:items-center gap-3 sm:gap-4">
                            <div className="flex flex-col items-center justify-center min-w-[50px] sm:min-w-[60px] text-center">
                              <span className={`text-xs sm:text-sm font-bold ${isNext ? 'text-primary' : 'text-foreground'}`}>
                                {appt.appointment_time}
                              </span>
                              <span className="text-[10px] sm:text-xs text-muted-foreground mt-0.5">Today</span>
                            </div>
                            
                            <div className="h-8 sm:h-10 w-px bg-border/50 hidden sm:block"></div>
                            
                            <div className="flex items-center gap-2.5 sm:gap-3">
                              <Avatar className={`w-9 h-9 sm:w-10 sm:h-10 ${isNext ? 'ring-2 ring-primary ring-offset-2 ring-offset-background' : ''}`}>
                                <AvatarFallback className={`${isNext ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'} text-xs sm:text-sm font-medium`}>
                                  {patient ? patient.name.substring(0, 2).toUpperCase() : 'PT'}
                                </AvatarFallback>
                              </Avatar>
                              <div>
                                <h4 className="text-sm sm:text-base font-semibold text-foreground flex items-center gap-1.5 sm:gap-2">
                                  {patient ? patient.name : `Patient #${appt.patient_id.substring(0, 6)}`}
                                  {isNext && <Badge variant="default" className="h-4 sm:h-5 px-1 sm:px-1.5 text-[9px] sm:text-[10px] uppercase tracking-wider bg-primary">Next</Badge>}
                                </h4>
                                <div className="flex flex-wrap items-center gap-2 sm:gap-3 mt-0.5 sm:mt-1 text-[10px] sm:text-xs text-muted-foreground">
                                  <span className="flex items-center gap-1">
                                    <FileText className="w-2.5 h-2.5 sm:w-3 sm:h-3" />
                                    <span className="line-clamp-1">{appt.reason || "Consultation"}</span>
                                  </span>
                                  {patient?.blood_group && (
                                    <>
                                      <span className="w-1 h-1 rounded-full bg-border hidden sm:block"></span>
                                      <span className="text-rose-500 font-medium hidden sm:block">{patient.blood_group}</span>
                                    </>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                          
                          <div className="flex items-center gap-2 mt-2 sm:mt-0 pl-[62px] sm:pl-0">
                            <Button variant="outline" size="sm" className="rounded-full shadow-sm hover:bg-primary/5 hover:text-primary transition-colors opacity-100 sm:opacity-0 group-hover:opacity-100 h-8 text-[11px] sm:text-xs px-3">
                              Record
                            </Button>
                            <Button size="sm" className="rounded-full shadow-sm h-8 text-[11px] sm:text-xs px-4">
                              Start
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-[20px] border-border/50 shadow-sm overflow-hidden hidden sm:block">
            <CardHeader className="flex flex-row items-center justify-between border-b bg-muted/10 pb-3 sm:pb-4 px-4 sm:px-6 pt-4 sm:pt-6">
              <div>
                <CardTitle className="text-base sm:text-lg">Patient Flow</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="p-4 sm:p-6">
              <div className="h-[200px] sm:h-[250px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorPatients" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                    <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} dy={10} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                    <RechartsTooltip 
                      contentStyle={{ borderRadius: '12px', border: '1px solid hsl(var(--border))', boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }}
                      itemStyle={{ color: 'hsl(var(--foreground))', fontWeight: 500 }}
                    />
                    <Area type="monotone" dataKey="patients" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorPatients)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
