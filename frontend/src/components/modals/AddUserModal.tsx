"use client";

import { useState } from "react";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { createUser, createDoctor } from "@/lib/api";
import { Role } from "@/lib/rbac";
import { auth } from "@/lib/firebase";
import { sendPasswordResetEmail } from "firebase/auth";
import { Loader2, UserPlus } from "lucide-react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { Tenant } from "@/types/api";
import { cn } from "@/lib/utils";

interface AddUserModalProps {
  tenants?: Tenant[];
  fixedRole?: Role;
  fixedTenantId?: string;
  triggerText?: string;
}

export function AddUserModal({ tenants = [], fixedRole, fixedTenantId, triggerText = "Add User" }: AddUserModalProps) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<string>(fixedRole || "");
  const [tenantId, setTenantId] = useState<string>(fixedTenantId || "");
  
  // Doctor specific fields
  const [specialization, setSpecialization] = useState("");
  const [experience, setExperience] = useState<number>(0);
  const [fee, setFee] = useState<number>(500);

  const [loading, setLoading] = useState(false);
  const queryClient = useQueryClient();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      // 1. Create the user on the backend
      await createUser({
        email,
        name,
        role,
        tenant_id: tenantId,
      });

      // 2. Trigger Firebase Password Reset Email
      await sendPasswordResetEmail(auth, email);

      // 3. If role is doctor, we also create the Doctor record
      if (role === Role.DOCTOR) {
         await createDoctor({
            name,
            specialization,
            qualifications: ["MBBS"], // Basic default
            experience_years: experience,
            languages: ["English"],
            consultation_fee: fee,
            availability_schedule: { "monday": ["09:00-17:00"] },
            is_active: true,
            tenant_id: tenantId
         });
         queryClient.invalidateQueries({ queryKey: ["doctors"] });
      }

      toast.success("User created! An email has been sent to them to set their password.");
      setOpen(false);
      setName("");
      setEmail("");
      setSpecialization("");
      setExperience(0);
      setFee(500);
      if (!fixedRole) setRole("");
      if (!fixedTenantId) setTenantId("");
    } catch (error: any) {
      let errorMessage = "Failed to create user";
      if (error.response?.data?.detail) {
        if (typeof error.response.data.detail === "string") {
          errorMessage = error.response.data.detail;
        } else if (Array.isArray(error.response.data.detail)) {
          errorMessage = error.response.data.detail.map((e: any) => e.msg).join(", ");
        }
      } else if (error.message) {
        errorMessage = error.message;
      }
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const isDoctor = role === Role.DOCTOR || fixedRole === Role.DOCTOR;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger className={cn(buttonVariants({ className: "gap-2" }))}>
        <UserPlus className="w-4 h-4" />
        {triggerText}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create New User</DialogTitle>
          <DialogDescription>
            Register a new user. They will receive an email to set their password.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Full Name</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="email">Email Address</Label>
            <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>

          {!fixedRole && (
            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <Select value={role} onValueChange={(v) => setRole(v || "")} required>
                <SelectTrigger>
                  <SelectValue placeholder="Select a role" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={Role.HOSPITAL_ADMIN}>Hospital Admin</SelectItem>
                  <SelectItem value={Role.DOCTOR}>Doctor</SelectItem>
                  <SelectItem value={Role.STAFF}>Staff</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          {!fixedTenantId && (
            <div className="space-y-2">
              <Label htmlFor="tenant">Assign to Hospital</Label>
              <Select value={tenantId} onValueChange={(v) => setTenantId(v || "")} required>
                <SelectTrigger>
                  <SelectValue placeholder="Select a hospital" />
                </SelectTrigger>
                <SelectContent>
                  {tenants.map(t => (
                    <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Conditional Doctor Fields */}
          {isDoctor && (
            <>
              <div className="space-y-2">
                <Label htmlFor="specialty">Specialization</Label>
                <Input 
                  id="specialty" 
                  value={specialization} 
                  onChange={(e) => setSpecialization(e.target.value)} 
                  placeholder="e.g. Cardiologist" 
                  required={isDoctor} 
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="experience">Experience (Years)</Label>
                  <Input 
                    id="experience" 
                    type="number"
                    min="0"
                    value={experience} 
                    onChange={(e) => setExperience(parseInt(e.target.value) || 0)} 
                    required={isDoctor} 
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="fee">Consultation Fee (₹)</Label>
                  <Input 
                    id="fee" 
                    type="number"
                    min="0"
                    value={fee} 
                    onChange={(e) => setFee(parseInt(e.target.value) || 0)} 
                    required={isDoctor} 
                  />
                </div>
              </div>
            </>
          )}

          <DialogFooter className="pt-4">
            <Button type="button" variant="outline" onClick={() => setOpen(false)} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading || !name || !email || !role || !tenantId || (isDoctor && (!specialization))}>
              {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              Create User
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
