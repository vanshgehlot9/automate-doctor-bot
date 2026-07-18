"use client";

import React, { useState, useEffect } from "react";
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
import { supabase } from "@/lib/supabase";
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
  customTrigger?: React.ReactNode;
}

export function AddUserModal({ tenants = [], fixedRole, fixedTenantId, triggerText = "Add User", customTrigger }: AddUserModalProps) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<string>(fixedRole || "");
  const [tenantId, setTenantId] = useState<string>(fixedTenantId || "");
  
  // Doctor specific fields
  const [specialization, setSpecialization] = useState("");
  const [experience, setExperience] = useState<number>(0);
  const [fee, setFee] = useState<number>(500);
  const [whatsappNumber, setWhatsappNumber] = useState("");

  const [loading, setLoading] = useState(false);
  const queryClient = useQueryClient();

  const [inviteLink, setInviteLink] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const metadata: any = { name };
      if (isDoctor) {
        metadata.specialization = specialization;
        metadata.experience = experience;
        metadata.fee = fee;
        metadata.whatsapp_number = whatsappNumber || undefined;
      }

      // Import the action dynamically to avoid Next.js client-side errors
      const { createInvitation } = await import("@/app/invite/actions");
      
      const res = await createInvitation({
        tenantId,
        email,
        role: isDoctor ? Role.DOCTOR : role,
        metadata
      });

      if (res.error) {
        throw new Error(res.error);
      }

      const generatedLink = `${window.location.origin}/invite/${res.token}`;
      setInviteLink(generatedLink);
      toast.success("Invitation generated successfully!");
      
    } catch (error: any) {
      toast.error(error.message || "Failed to generate invitation");
    } finally {
      setLoading(false);
    }
  };

  const isDoctor = role === Role.DOCTOR || fixedRole === Role.DOCTOR;

  return (
    <>
      {customTrigger ? (
        // Render custom trigger outside Dialog to avoid nested <button> issue with base-ui
        React.cloneElement(customTrigger as React.ReactElement<any>, {
          onClick: (e: React.MouseEvent) => {
            (customTrigger as React.ReactElement<any>).props.onClick?.(e);
            setOpen(true);
          }
        })
      ) : null}
      <Dialog open={open} onOpenChange={setOpen}>
        {!customTrigger && (
          <DialogTrigger className={cn(buttonVariants({ className: "gap-2" }))}>
            <UserPlus className="w-4 h-4" />
            {triggerText}
          </DialogTrigger>
        )}
      <DialogContent className="sm:max-w-[425px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{inviteLink ? "Invitation Created" : "Create New User"}</DialogTitle>
          <DialogDescription>
            {inviteLink 
              ? "The invitation link has been generated. Share this with the user."
              : "Register a new user. You will receive an invite link to send them."}
          </DialogDescription>
        </DialogHeader>
        
        {inviteLink ? (
          <div className="space-y-4 pt-4">
            <div className="p-3 bg-muted rounded-md break-all text-sm font-mono text-muted-foreground border">
              {inviteLink}
            </div>
            <div className="flex gap-2">
              <Button 
                className="w-full"
                onClick={() => {
                  navigator.clipboard.writeText(inviteLink);
                  toast.success("Link copied to clipboard!");
                }}
              >
                Copy Link
              </Button>
            </div>
            <DialogFooter className="pt-4">
              <Button type="button" variant="outline" onClick={() => {
                setOpen(false);
                setTimeout(() => setInviteLink(null), 300);
                setName("");
                setEmail("");
                setSpecialization("");
                setExperience(0);
                setFee(500);
                setWhatsappNumber("");
                if (!fixedRole) setRole("");
                if (!fixedTenantId) setTenantId("");
              }}>
                Close
              </Button>
            </DialogFooter>
          </div>
        ) : (
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
              <div className="space-y-2">
                <Label htmlFor="whatsapp_number">
                  WhatsApp Number
                  <span className="text-muted-foreground text-xs ml-2">(for Doctor Bot, e.g. 919876543210)</span>
                </Label>
                <Input 
                  id="whatsapp_number" 
                  value={whatsappNumber} 
                  onChange={(e) => setWhatsappNumber(e.target.value)} 
                  placeholder="91XXXXXXXXXX (country code + number)"
                />
              </div>
            </>
          )}

          <DialogFooter className="pt-4">
            <Button type="button" variant="outline" onClick={() => setOpen(false)} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading || !name || !email || !role || !tenantId || (isDoctor && (!specialization))}>
              {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              Generate Invite Link
            </Button>
          </DialogFooter>
        </form>
        )}
      </DialogContent>
    </Dialog>
    </>
  );
}
