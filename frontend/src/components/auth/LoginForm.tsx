"use client";

import { useState } from "react";
import { signInWithEmailAndPassword, signInWithPopup, GoogleAuthProvider } from "firebase/auth";
import { auth, db } from "@/lib/firebase";
import { doc, getDoc } from "firebase/firestore";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { UserProfile, Role } from "@/lib/rbac";
import { Loader2, ShieldCheck, Activity } from "lucide-react";
import { toast } from "sonner";
import { Checkbox } from "@/components/ui/checkbox";
import Image from "next/image";

export function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleRedirect = (role: Role) => {
    switch (role) {
      case Role.SUPER_ADMIN:
        router.push("/super-admin");
        break;
      case Role.HOSPITAL_ADMIN:
        router.push("/admin");
        break;
      case Role.DOCTOR:
        router.push("/doctor");
        break;
      default:
        router.push("/staff");
    }
  };

  const setSessionCookie = (role: Role) => {
    let cookieName = "staff_session";
    if (role === Role.SUPER_ADMIN || role === Role.HOSPITAL_ADMIN) cookieName = "super_admin_session";
    if (role === Role.DOCTOR) cookieName = "doctor_session";
    document.cookie = `${cookieName}=true; path=/; max-age=86400; SameSite=Lax`;
  };

  const onLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      const userDoc = await getDoc(doc(db, "users", userCredential.user.uid));
      if (userDoc.exists()) {
        const profile = userDoc.data() as UserProfile;
        toast.success("Login successful!");
        setSessionCookie(profile.role);
        handleRedirect(profile.role);
      } else {
        toast.error("User profile not found. Please contact support.");
      }
    } catch (error: any) {
      toast.error(error.message || "Failed to login");
    } finally {
      setLoading(false);
    }
  };

  const onGoogleLogin = async () => {
    setLoading(true);
    const provider = new GoogleAuthProvider();
    try {
      const userCredential = await signInWithPopup(auth, provider);
      const userDoc = await getDoc(doc(db, "users", userCredential.user.uid));
      if (userDoc.exists()) {
        const profile = userDoc.data() as UserProfile;
        toast.success("Google Login successful!");
        setSessionCookie(profile.role);
        handleRedirect(profile.role);
      } else {
        toast.error("User profile not found. Please contact support.");
      }
    } catch (error: any) {
      toast.error(error.message || "Failed to login with Google");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-[440px] space-y-8">
      
      {/* Mobile Branding (Visible only on small screens) */}
      <div className="lg:hidden flex items-center justify-center gap-2 mb-6">
        <div className="w-8 h-8 rounded-lg overflow-hidden relative shadow-md">
          <Image src="/aatomate.jpeg" alt="Aatomate Medical OS" fill className="object-cover" />
        </div>
        <span className="text-lg font-bold tracking-tight text-slate-900">Aatomate Medical OS</span>
      </div>

      {/* Main Login Panel */}
      <div className="bg-white p-8 sm:p-10 rounded-[24px] shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100">
        <div className="text-center mb-8">
          <div className="w-12 h-12 bg-slate-50 border border-slate-100 rounded-xl overflow-hidden relative mx-auto mb-4 shadow-sm">
             <Image src="/aatomate.jpeg" alt="Aatomate Medical OS" fill className="object-cover" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">Welcome Back</h2>
          <p className="text-sm text-slate-500 mt-2">Sign in to continue to your workspace.</p>
        </div>

        <form onSubmit={onLogin} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="email" className="text-slate-700 font-medium">Email Address</Label>
            <Input 
              id="email" 
              type="email" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)} 
              placeholder="doctor@hospital.com" 
              className="h-11 bg-slate-50 border-slate-200 focus-visible:ring-blue-500 focus-visible:bg-white transition-all shadow-sm rounded-xl"
              required 
            />
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="password" className="text-slate-700 font-medium">Password</Label>
              <a href="#" className="text-sm text-blue-600 hover:text-blue-700 font-medium">Forgot password?</a>
            </div>
            <Input 
              id="password" 
              type="password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              placeholder="••••••••" 
              className="h-11 bg-slate-50 border-slate-200 focus-visible:ring-blue-500 focus-visible:bg-white transition-all shadow-sm rounded-xl"
              required 
            />
          </div>

          <div className="flex items-center space-x-2 pt-1 pb-2">
            <Checkbox id="remember" className="border-slate-300 text-blue-600 focus-visible:ring-blue-500 rounded-[4px]" />
            <label
              htmlFor="remember"
              className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 text-slate-600 cursor-pointer"
            >
              Remember me
            </label>
          </div>

          <Button type="submit" className="w-full h-11 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-sm transition-all" disabled={loading}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Sign In
          </Button>
        </form>

        <div className="relative my-8">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t border-slate-200" />
          </div>
          <div className="relative flex justify-center text-xs">
            <span className="bg-white px-3 text-slate-400 font-medium">Single Sign-On</span>
          </div>
        </div>

        <Button variant="outline" type="button" className="w-full h-11 border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium rounded-xl shadow-sm transition-all" onClick={onGoogleLogin} disabled={loading}>
          <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
            <path d="M1 1h22v22H1z" fill="none" />
          </svg>
          Continue with Google
        </Button>
      </div>

      {/* Security Indicators */}
      <div className="flex flex-col items-center justify-center text-center space-y-1 mt-6">
        <div className="flex items-center gap-1.5 text-slate-500 mb-1">
          <ShieldCheck className="w-4 h-4 text-emerald-500" />
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">Protected with enterprise-grade encryption</span>
        </div>
        <p className="text-[10px] text-slate-400 font-medium">
          HIPAA-ready architecture • Secure authentication • End-to-end encrypted
        </p>
      </div>

    </div>
  );
}
