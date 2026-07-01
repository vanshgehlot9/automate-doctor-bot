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
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

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
    <div className="w-full max-w-md space-y-8 bg-card p-8 rounded-2xl shadow-sm border">
      <div className="text-center">
        <h2 className="text-3xl font-bold tracking-tight">Welcome Back</h2>
        <p className="text-sm text-muted-foreground mt-2">Sign in to your Aatomate account</p>
      </div>

      <form onSubmit={onLogin} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input 
            id="email" 
            type="email" 
            value={email} 
            onChange={(e) => setEmail(e.target.value)} 
            placeholder="doctor@hospital.com" 
            required 
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input 
            id="password" 
            type="password" 
            value={password} 
            onChange={(e) => setPassword(e.target.value)} 
            placeholder="••••••••" 
            required 
          />
        </div>

        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
          Sign In
        </Button>
      </form>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-card px-2 text-muted-foreground">Or continue with</span>
        </div>
      </div>

      <Button variant="outline" type="button" className="w-full" onClick={onGoogleLogin} disabled={loading}>
        Google
      </Button>
    </div>
  );
}
