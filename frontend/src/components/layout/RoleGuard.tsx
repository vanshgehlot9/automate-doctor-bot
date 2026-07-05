"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { Role, hasPermission } from "@/lib/rbac";
import { Loader2 } from "lucide-react";

interface RoleGuardProps {
  children: React.ReactNode;
  allowedRoles: Role[];
  fallback?: React.ReactNode;
}

export function RoleGuard({ children, allowedRoles, fallback }: RoleGuardProps) {
  const { user, userProfile, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      if (!user || !userProfile) {
        router.push("/login"); // Need to make sure this route exists and uses Supabase Auth
      } else if (!hasPermission(userProfile.role, allowedRoles)) {
        router.push("/unauthorized"); // Need to create an unauthorized page
      }
    }
  }, [loading, user, userProfile, router, allowedRoles]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!user || !userProfile || !hasPermission(userProfile.role, allowedRoles)) {
    return fallback || null;
  }

  return <>{children}</>;
}
