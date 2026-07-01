"use client";

import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [isAuth, setIsAuth] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("superAdminAuthToken");
    if (!token) {
      router.push("/super-admin/login");
    } else {
      setIsAuth(true);
    }
  }, [router]);

  if (!isAuth) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      <Sidebar />
      <div className="flex flex-col min-h-screen">
        <Topbar userProfile={{ name: 'Super Admin', role: 'super_admin' } as any} />
        <main className="flex-1 p-8 ml-64 overflow-auto">
          <div className="max-w-7xl mx-auto space-y-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
