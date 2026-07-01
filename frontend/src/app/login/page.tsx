import { LoginForm } from "@/components/auth/LoginForm";
import { CheckCircle2, Hospital, ShieldCheck, Activity } from "lucide-react";
import Image from "next/image";

export default function LoginPage() {
  return (
    <div className="min-h-screen w-full flex bg-slate-50">
      
      {/* Left Side - Branding (Hidden on Mobile) */}
      <div className="hidden lg:flex w-[45%] bg-slate-900 text-white flex-col justify-between relative overflow-hidden">
        {/* Very subtle background grid/pattern */}
        <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-5 pointer-events-none mix-blend-overlay"></div>
        <div className="absolute inset-0 bg-gradient-to-b from-slate-900/50 via-transparent to-slate-900/80 pointer-events-none"></div>

        {/* Top Section */}
        <div className="p-12 xl:p-16 relative z-10">
          <div className="flex items-center gap-3 mb-16">
            <div className="w-12 h-12 bg-white rounded-xl overflow-hidden relative shadow-lg flex items-center justify-center p-1">
              <Image src="/aatomate.jpeg" alt="Aatomate Medical OS" fill className="object-contain rounded-lg" />
            </div>
            <span className="text-xl font-bold tracking-tight">Aatomate Medical OS</span>
          </div>

          <h1 className="text-4xl xl:text-5xl font-bold tracking-tight mb-6 leading-[1.15]">
            AI-powered workflow platform for modern hospitals and clinics.
          </h1>
          
          <div className="space-y-5 mt-12 text-slate-300">
            <div className="flex items-center gap-3">
              <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0" />
              <span className="font-medium text-lg">Secure Patient Records</span>
            </div>
            <div className="flex items-center gap-3">
              <Hospital className="w-5 h-5 text-emerald-400 shrink-0" />
              <span className="font-medium text-lg">Multi-Hospital Architecture</span>
            </div>
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
              <span className="font-medium text-lg">Appointment Management</span>
            </div>
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
              <span className="font-medium text-lg">Digital Prescriptions</span>
            </div>
          </div>
        </div>

        {/* Bottom Section */}
        <div className="p-12 xl:p-16 relative z-10">
          <div className="flex -space-x-2 mb-4">
             {/* Mock user avatars for trust factor */}
             <div className="w-8 h-8 rounded-full bg-slate-700 border-2 border-slate-900"></div>
             <div className="w-8 h-8 rounded-full bg-slate-600 border-2 border-slate-900"></div>
             <div className="w-8 h-8 rounded-full bg-slate-500 border-2 border-slate-900"></div>
          </div>
          <p className="text-sm font-medium text-slate-400">
            Trusted by top hospitals and healthcare professionals worldwide.
          </p>
        </div>
      </div>

      {/* Right Side - Form */}
      <div className="w-full lg:w-[55%] flex items-center justify-center p-4 sm:p-8 relative">
        <LoginForm />
      </div>

    </div>
  );
}
