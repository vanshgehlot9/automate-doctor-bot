"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Trash2, Loader2, Stethoscope, Calendar, MessageCircle, Pencil, Check, X } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getDoctors, deleteDoctor, updateDoctor } from "@/lib/api";
import { useAuth } from "@/providers/AuthProvider";
import { Role } from "@/lib/rbac";
import { AddUserModal } from "@/components/modals/AddUserModal";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Doctor } from "@/types/api";

export default function AdminDoctorsPage() {
  const { userProfile } = useAuth();
  const queryClient = useQueryClient();
  const router = useRouter();
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Inline WhatsApp number editing state
  const [editingWaId, setEditingWaId] = useState<string | null>(null);
  const [editingWaValue, setEditingWaValue] = useState("");
  const [savingWaId, setSavingWaId] = useState<string | null>(null);

  const { data: doctors, isLoading: loadingDoctors } = useQuery({
    queryKey: ["doctors"],
    queryFn: getDoctors
  });

  const handleDeleteDoctor = async (id: string) => {
    if (!confirm("Are you sure you want to delete this doctor?")) return;
    setDeletingId(id);
    try {
      await deleteDoctor(id, userProfile?.tenantId);
      toast.success("Doctor deleted successfully");
      queryClient.invalidateQueries({ queryKey: ["doctors"] });
    } catch (error: any) {
      toast.error(error.message || "Failed to delete doctor");
    } finally {
      setDeletingId(null);
    }
  };

  const startEditWa = (doc: Doctor) => {
    setEditingWaId(doc.id);
    setEditingWaValue(doc.whatsapp_number || "");
  };

  const cancelEditWa = () => {
    setEditingWaId(null);
    setEditingWaValue("");
  };

  const saveWaNumber = async (docId: string) => {
    setSavingWaId(docId);
    try {
      await updateDoctor(docId, { whatsapp_number: editingWaValue || null }, userProfile?.tenantId);
      toast.success("WhatsApp number updated!");
      queryClient.invalidateQueries({ queryKey: ["doctors"] });
      cancelEditWa();
    } catch (error: any) {
      toast.error(error.message || "Failed to update WhatsApp number");
    } finally {
      setSavingWaId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Doctors</h1>
          <p className="text-muted-foreground mt-1">Manage all doctors in your hospital.</p>
        </div>
        <AddUserModal fixedRole={Role.DOCTOR} fixedTenantId={userProfile?.tenantId} triggerText="Add Doctor" />
      </div>

      {/* WhatsApp Bot Info Banner */}
      <div className="flex items-start gap-3 p-4 rounded-lg border border-green-500/30 bg-green-500/5">
        <MessageCircle className="w-5 h-5 text-green-500 mt-0.5 shrink-0" />
        <div>
          <p className="text-sm font-medium text-green-600 dark:text-green-400">Doctor WhatsApp Bot</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Add each doctor&apos;s personal WhatsApp number below so they can access patient records, 
            appointments, and write prescriptions directly from WhatsApp. 
            Format: <code className="bg-muted px-1 rounded">91XXXXXXXXXX</code> (country code + number, no + or spaces).
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Stethoscope className="w-5 h-5 text-primary" />
            Doctors Directory
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loadingDoctors ? (
            <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-muted-foreground" /></div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Specialty</TableHead>
                  <TableHead>Fee</TableHead>
                  <TableHead>
                    <span className="flex items-center gap-1.5">
                      <MessageCircle className="w-3.5 h-3.5 text-green-500" />
                      WhatsApp (Bot)
                    </span>
                  </TableHead>
                  <TableHead className="w-[160px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {doctors?.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-6 text-muted-foreground">No doctors found.</TableCell>
                  </TableRow>
                ) : (
                  doctors?.map((doc) => (
                    <TableRow key={doc.id}>
                      <TableCell className="font-medium">{doc.name}</TableCell>
                      <TableCell>{doc.specialization}</TableCell>
                      <TableCell>₹{doc.consultation_fee}</TableCell>

                      {/* WhatsApp Number Cell — inline editable */}
                      <TableCell>
                        {editingWaId === doc.id ? (
                          <div className="flex items-center gap-1.5">
                            <Input
                              className="h-7 text-xs w-36"
                              value={editingWaValue}
                              onChange={(e) => setEditingWaValue(e.target.value)}
                              placeholder="91XXXXXXXXXX"
                              autoFocus
                            />
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7 text-green-600 hover:bg-green-50 hover:text-green-700"
                              disabled={savingWaId === doc.id}
                              onClick={() => saveWaNumber(doc.id)}
                            >
                              {savingWaId === doc.id
                                ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                : <Check className="w-3.5 h-3.5" />}
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7 text-muted-foreground hover:text-destructive"
                              onClick={cancelEditWa}
                            >
                              <X className="w-3.5 h-3.5" />
                            </Button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1.5 group">
                            {doc.whatsapp_number ? (
                              <Badge variant="outline" className="text-green-600 border-green-400/50 gap-1 font-mono text-xs">
                                <MessageCircle className="w-2.5 h-2.5" />
                                {doc.whatsapp_number}
                              </Badge>
                            ) : (
                              <span className="text-xs text-muted-foreground italic">Not set</span>
                            )}
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                              onClick={() => startEditWa(doc)}
                            >
                              <Pencil className="w-3 h-3" />
                            </Button>
                          </div>
                        )}
                      </TableCell>

                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            className="gap-2"
                            onClick={() => router.push(`/admin/doctors/${doc.id}/schedule`)}
                          >
                            <Calendar className="w-4 h-4" /> Schedule
                          </Button>
                          <Button 
                            variant="ghost" 
                            size="icon"
                            onClick={() => handleDeleteDoctor(doc.id)}
                            disabled={deletingId === doc.id}
                            className="text-destructive hover:bg-destructive/10"
                          >
                            {deletingId === doc.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
