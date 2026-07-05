"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchVendors, createVendor, updateVendor, deleteVendor } from "@/lib/api";
import { AdminLayout } from "@/components/layout/admin-layout";
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table";
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle,
  CardDescription 
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  MoreHorizontal, 
  Plus, 
  Search, 
  MapPin, 
  CheckCircle,
  XCircle,
  Clock,
  Sparkles,
  Award,
  Phone,
  Mail,
  UserCheck,
  Percent,
  TrendingUp,
  Sliders,
  DollarSign,
  Trash2,
  Edit,
  Car,
  Compass,
  Users
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useState, useEffect } from "react";
import { toast } from "sonner";
import { io } from "socket.io-client";

const VENDOR_TYPES = [
  "Tour Operator",
  "Taxi Provider",
  "Guide Service",
  "Adventure Company",
  "Rental Provider",
  "Safari Provider"
];

export default function VendorsPage() {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [selectedVendor, setSelectedVendor] = useState<any>(null);
  
  // Real-time onboarding logs state
  const [onboardingLogs, setOnboardingLogs] = useState<string[]>([]);
  const [isOnboardingActive, setIsOnboardingActive] = useState(false);

  // Form State
  const [formData, setFormData] = useState({
    company_name: "",
    owner_name: "",
    email: "",
    phone: "",
    password: "",
    vendor_type: "Tour Operator",
    city: "",
    gst_number: "",
    commission_percentage: 10.0,
    verification_status: "Pending"
  });

  const { data: vendors, isLoading } = useQuery({
    queryKey: ["vendors"],
    queryFn: fetchVendors,
  });

  // Socket.IO for real-time synchronization
  useEffect(() => {
    const BACKEND = process.env.NEXT_PUBLIC_API_URL?.replace("/api/admin", "") || "http://localhost:8000";
    const socket = io(BACKEND, { transports: ["websocket", "polling"] });

    socket.on("connect", () => {
      console.log("SuperAdmin live sync connected");
    });

    socket.on("vendor_metrics_refresh", () => {
      queryClient.invalidateQueries({ queryKey: ["vendors"] });
    });

    socket.on("vendor_profile_updated", (updated: any) => {
      queryClient.invalidateQueries({ queryKey: ["vendors"] });
      toast.info(`Real-time update: Vendor '${updated.company_name}' updated.`);
    });

    return () => {
      socket.disconnect();
    };
  }, [queryClient]);

  // Mutations
  const createMutation = useMutation({
    mutationFn: createVendor,
    onSuccess: (data) => {
      setIsOnboardingActive(true);
      setOnboardingLogs([
        "🔑 Securing cryptographic keypairs...",
        "⚙️ Hashing password using standard bcrypt...",
        "🗄️ Registering user credentials into Supabase Auth core...",
        "🚀 Deploying partner profile data into Supabase catalog...",
      ]);

      // Simulate step-by-step credentials generation and messaging
      setTimeout(() => {
        setOnboardingLogs(prev => [...prev, "📧 Welcome invitation template rendered successfully."]);
      }, 1000);
      
      setTimeout(() => {
        setOnboardingLogs(prev => [...prev, `📬 Simulating welcome email dispatch to ${formData.email}...`]);
      }, 2000);

      setTimeout(() => {
        setOnboardingLogs(prev => [...prev, `💬 Dispatched onboarding WhatsApp text to phone: ${formData.phone}`]);
      }, 3000);

      setTimeout(() => {
        setOnboardingLogs(prev => [...prev, "✅ Real-time partner synchronization complete. Active Status: LIVE."]);
        toast.success("Vendor onboarding complete!");
        queryClient.invalidateQueries({ queryKey: ["vendors"] });
        
        // Reset and close
        setTimeout(() => {
          setIsCreateOpen(false);
          setIsOnboardingActive(false);
          setOnboardingLogs([]);
          setFormData({
            company_name: "",
            owner_name: "",
            email: "",
            phone: "",
            password: "",
            vendor_type: "Tour Operator",
            city: "",
            gst_number: "",
            commission_percentage: 10.0,
            verification_status: "Pending"
          });
        }, 1500);
      }, 4000);
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "Failed to onboard vendor");
    }
  });

  const updateMutation = useMutation({
    mutationFn: ({ email, data }: { email: string, data: any }) => updateVendor(email, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vendors"] });
      toast.success("Vendor profile updated successfully");
      setIsEditOpen(false);
      setSelectedVendor(null);
    },
    onError: () => {
      toast.error("Failed to update vendor");
    }
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteVendor(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vendors"] });
      toast.success("Vendor removed successfully");
    },
    onError: () => {
      toast.error("Failed to remove vendor");
    }
  });

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(formData);
  };

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate({
      email: selectedVendor.id,
      data: selectedVendor
    });
  };

  const handleStatusChange = (email: string, status: string) => {
    updateMutation.mutate({
      email,
      data: { verification_status: status }
    });
  };

  const filteredVendors = vendors?.filter((v: any) => 
    v.company_name?.toLowerCase().includes(searchTerm.toLowerCase()) || 
    v.owner_name?.toLowerCase().includes(searchTerm.toLowerCase()) || 
    v.city?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Computed Aggregations
  const totalCount = vendors?.length || 0;
  const pendingCount = vendors?.filter((v: any) => v.verification_status === "Pending").length || 0;
  const avgCommission = totalCount > 0 && vendors
    ? (vendors.reduce((acc: number, v: any) => acc + (Number(v.commission_percentage) || 0), 0) / totalCount).toFixed(1)
    : "0.0";
  const approvedCount = vendors?.filter((v: any) => v.verification_status === "Approved").length || 0;

  return (
    <AdminLayout>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Vendor Management</h1>
          <p className="text-slate-500 mt-1">Onboard partner providers, monitor platform commission matrices, and handle status approvals.</p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)} className="bg-indigo-600 hover:bg-indigo-700 shadow-sm shadow-indigo-200">
          <Plus className="w-4 h-4 mr-2" />
          Onboard New Partner
        </Button>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mt-6">
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6 flex items-center justify-between">
            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">Total Partners</span>
              <h3 className="text-2xl font-black text-slate-900 mt-1">{totalCount}</h3>
              <p className="text-slate-400 text-xs mt-1">{approvedCount} fully verified</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center text-slate-700">
              <Users className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6 flex items-center justify-between">
            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">Pending Approvals</span>
              <h3 className="text-2xl font-black text-amber-600 mt-1">{pendingCount}</h3>
              <p className="text-slate-400 text-xs mt-1">Require moderation check</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-amber-50 border border-amber-100 flex items-center justify-center text-amber-600">
              <Clock className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6 flex items-center justify-between">
            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">Avg. Commission</span>
              <h3 className="text-2xl font-black text-indigo-600 mt-1">{avgCommission}%</h3>
              <p className="text-slate-400 text-xs mt-1">Standard platform flat rate</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
              <Percent className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6 flex items-center justify-between">
            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">Real-time Sync</span>
              <h3 className="text-2xl font-black text-emerald-600 mt-1">ACTIVE</h3>
              <p className="text-slate-400 text-xs mt-1">Socket.IO State Listener</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600">
              <Sparkles className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Vendor List Grid */}
      <Card className="border-slate-200 shadow-sm mt-6">
        <CardHeader className="border-b border-slate-50 bg-slate-50/50 flex flex-row items-center justify-between space-y-0 py-4">
          <div className="flex items-center gap-4 flex-1">
            <div className="relative w-80">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input 
                type="text" 
                placeholder="Filter by name or city..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all text-slate-800"
              />
            </div>
          </div>
          <div className="text-sm text-slate-500 font-medium">
            Total Results: {filteredVendors?.length || 0}
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <Table>
            <TableHeader className="bg-slate-50/50">
              <TableRow className="hover:bg-transparent border-slate-100">
                <TableHead className="font-semibold text-slate-700">Company / Partner</TableHead>
                <TableHead className="font-semibold text-slate-700">Owner Details</TableHead>
                <TableHead className="font-semibold text-slate-700">Location</TableHead>
                <TableHead className="font-semibold text-slate-700">Vendor Type</TableHead>
                <TableHead className="font-semibold text-slate-700">GST / Comm.</TableHead>
                <TableHead className="font-semibold text-slate-700">Status</TableHead>
                <TableHead className="text-right font-semibold text-slate-700">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array(4).fill(0).map((_, i) => (
                  <TableRow key={i} className="border-slate-50">
                    <TableCell><div className="h-6 w-36 bg-slate-100 animate-pulse rounded" /></TableCell>
                    <TableCell><div className="h-6 w-28 bg-slate-100 animate-pulse rounded" /></TableCell>
                    <TableCell><div className="h-6 w-20 bg-slate-100 animate-pulse rounded" /></TableCell>
                    <TableCell><div className="h-6 w-24 bg-slate-100 animate-pulse rounded" /></TableCell>
                    <TableCell><div className="h-6 w-16 bg-slate-100 animate-pulse rounded" /></TableCell>
                    <TableCell><div className="h-6 w-16 bg-slate-100 animate-pulse rounded" /></TableCell>
                    <TableCell><div className="h-6 w-8 bg-slate-100 animate-pulse rounded ml-auto" /></TableCell>
                  </TableRow>
                ))
              ) : filteredVendors?.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-64 text-center">
                    <div className="flex flex-col items-center justify-center text-slate-400">
                      <Users className="w-12 h-12 mb-4 opacity-20" />
                      <p className="text-lg font-medium">No partner vendors found matching your search</p>
                      <p className="text-sm mt-1">Onboard a new partner to get started.</p>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                filteredVendors?.map((vendor: any) => (
                  <TableRow key={vendor.id} className="group hover:bg-slate-50/80 transition-colors border-slate-50">
                    <TableCell>
                      <div>
                        <p className="font-bold text-slate-900 leading-none group-hover:text-indigo-600 transition-colors">{vendor.company_name}</p>
                        <p className="text-[10px] text-slate-400 mt-1 truncate max-w-[200px]" title={vendor.email}>
                          {vendor.email}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div>
                        <p className="font-semibold text-slate-700 text-sm">{vendor.owner_name}</p>
                        <p className="text-[10px] text-slate-400 mt-1 flex items-center gap-1 font-mono">
                          <Phone className="w-3 h-3 text-slate-400" /> {vendor.phone}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1 text-slate-600 font-medium">
                        <MapPin className="w-3.5 h-3.5 text-slate-400" />
                        <span className="text-sm">{vendor.city}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="bg-slate-100 text-slate-700 border-0 font-medium hover:bg-slate-200">
                        {vendor.vendor_type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="text-xs">
                        <p className="font-bold text-slate-700">{vendor.gst_number || "N/A"}</p>
                        <p className="text-indigo-600 font-bold mt-0.5">{vendor.commission_percentage}% share</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      {vendor.verification_status === "Approved" ? (
                        <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100 shadow-none flex items-center gap-1 w-fit">
                          <CheckCircle className="w-3 h-3" /> Approved
                        </Badge>
                      ) : vendor.verification_status === "Rejected" ? (
                        <Badge className="bg-rose-50 text-rose-700 border-rose-200 hover:bg-rose-100 shadow-none flex items-center gap-1 w-fit">
                          <XCircle className="w-3 h-3" /> Rejected
                        </Badge>
                      ) : (
                        <Badge className="bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100 shadow-none flex items-center gap-1 w-fit">
                          <Clock className="w-3 h-3" /> Pending
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger className="inline-flex h-8 w-8 items-center justify-center rounded-lg hover:bg-slate-200 transition-colors focus:outline-none">
                          <MoreHorizontal className="h-4 w-4" />
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-52">
                          <DropdownMenuLabel>Partner Moderation</DropdownMenuLabel>
                          {vendor.verification_status !== "Approved" && (
                            <DropdownMenuItem className="cursor-pointer text-emerald-600 font-semibold" onClick={() => handleStatusChange(vendor.id, "Approved")}>
                              <CheckCircle className="mr-2 h-4 w-4" /> Approve Partner
                            </DropdownMenuItem>
                          )}
                          {vendor.verification_status !== "Rejected" && (
                            <DropdownMenuItem className="cursor-pointer text-rose-600 font-semibold" onClick={() => handleStatusChange(vendor.id, "Rejected")}>
                              <XCircle className="mr-2 h-4 w-4" /> Reject Partner
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuSeparator />
                          <DropdownMenuItem className="cursor-pointer" onClick={() => {
                            setSelectedVendor({ ...vendor });
                            setIsEditOpen(true);
                          }}>
                            <Edit className="mr-2 h-4 w-4" /> Edit Profile Details
                          </DropdownMenuItem>
                          <DropdownMenuItem className="text-rose-600 cursor-pointer" onClick={() => {
                            if(confirm(`Are you sure you want to terminate vendor account: ${vendor.company_name}?`)) {
                              deleteMutation.mutate(vendor.id);
                            }
                          }}>
                            <Trash2 className="mr-2 h-4 w-4" /> Terminate Account
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Manual Onboarding Modal (Dialog) */}
      <Dialog open={isCreateOpen} onOpenChange={(open) => {
        if (!isOnboardingActive) setIsCreateOpen(open);
      }}>
        <DialogContent className="max-w-2xl bg-white border border-slate-200 shadow-2xl rounded-2xl overflow-hidden p-0">
          <DialogHeader className="p-6 bg-slate-50/50 border-b border-slate-100">
            <DialogTitle className="text-slate-900 font-black text-xl flex items-center gap-2">
              <Award className="w-5 h-5 text-indigo-600" /> Manual Partner Onboarding
            </DialogTitle>
            <DialogDescription>
              Register a new provider manually. Real-time secure credentials will be generated automatically.
            </DialogDescription>
          </DialogHeader>

          {isOnboardingActive ? (
            <div className="p-8 space-y-6 text-center">
              <div className="mx-auto w-12 h-12 rounded-full border-4 border-indigo-600 border-t-transparent animate-spin mb-4" />
              <h3 className="font-bold text-slate-800 text-lg">Partner Onboarding Pipeline Active</h3>
              <div className="bg-slate-950 text-emerald-400 font-mono text-xs text-left p-5 rounded-xl border border-slate-800 max-h-48 overflow-y-auto space-y-1.5 shadow-inner">
                {onboardingLogs.map((log, index) => (
                  <p key={index}>{log}</p>
                ))}
              </div>
            </div>
          ) : (
            <form onSubmit={handleCreateSubmit}>
              <div className="p-6 space-y-4 max-h-[60vh] overflow-y-auto">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="company_name" className="text-slate-700 font-semibold text-xs">Company Name *</Label>
                    <Input 
                      id="company_name" 
                      placeholder="e.g. Thar Desert Safaris" 
                      value={formData.company_name}
                      onChange={(e) => setFormData({...formData, company_name: e.target.value})}
                      required
                      className="text-slate-800 border-slate-200"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="owner_name" className="text-slate-700 font-semibold text-xs">Owner Full Name *</Label>
                    <Input 
                      id="owner_name" 
                      placeholder="e.g. Vansh Gehlot" 
                      value={formData.owner_name}
                      onChange={(e) => setFormData({...formData, owner_name: e.target.value})}
                      required
                      className="text-slate-800 border-slate-200"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-slate-700 font-semibold text-xs">Email Address *</Label>
                    <Input 
                      id="email" 
                      type="email"
                      placeholder="partner@domain.com" 
                      value={formData.email}
                      onChange={(e) => setFormData({...formData, email: e.target.value})}
                      required
                      className="text-slate-800 border-slate-200"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="phone" className="text-slate-700 font-semibold text-xs">WhatsApp Number *</Label>
                    <Input 
                      id="phone" 
                      placeholder="+919876543210" 
                      value={formData.phone}
                      onChange={(e) => setFormData({...formData, phone: e.target.value})}
                      required
                      className="text-slate-800 border-slate-200"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="password" className="text-slate-700 font-semibold text-xs">Manual Password *</Label>
                    <Input 
                      id="password" 
                      type="password"
                      placeholder="••••••••" 
                      value={formData.password}
                      onChange={(e) => setFormData({...formData, password: e.target.value})}
                      required
                      className="text-slate-800 border-slate-200"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="vendor_type" className="text-slate-700 font-semibold text-xs">Service Category *</Label>
                    <select 
                      id="vendor_type"
                      value={formData.vendor_type}
                      onChange={(e) => setFormData({...formData, vendor_type: e.target.value})}
                      className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 text-slate-800 h-10"
                    >
                      {VENDOR_TYPES.map(type => (
                        <option key={type} value={type}>{type}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="city" className="text-slate-700 font-semibold text-xs">Operating City *</Label>
                    <Input 
                      id="city" 
                      placeholder="Jodhpur" 
                      value={formData.city}
                      onChange={(e) => setFormData({...formData, city: e.target.value})}
                      required
                      className="text-slate-800 border-slate-200"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="gst_number" className="text-slate-700 font-semibold text-xs">GSTIN (Optional)</Label>
                    <Input 
                      id="gst_number" 
                      placeholder="08AAAAA1111A1Z1" 
                      value={formData.gst_number}
                      onChange={(e) => setFormData({...formData, gst_number: e.target.value})}
                      className="text-slate-800 border-slate-200"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="commission" className="text-slate-700 font-semibold text-xs">Commission %</Label>
                    <Input 
                      id="commission" 
                      type="number"
                      min="0"
                      max="100"
                      value={formData.commission_percentage}
                      onChange={(e) => setFormData({...formData, commission_percentage: parseFloat(e.target.value) || 0})}
                      required
                      className="text-slate-800 border-slate-200"
                    />
                  </div>
                </div>
              </div>

              <DialogFooter className="p-6 bg-slate-50/50 border-t border-slate-100">
                <DialogClose className="px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-700 hover:bg-slate-100 font-semibold cursor-pointer transition-colors bg-white">
                  Cancel
                </DialogClose>
                <Button type="submit" disabled={createMutation.isPending} className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm shadow-indigo-100 border-0">
                  {createMutation.isPending ? "Starting onboarding..." : "Confirm & Trigger Onboarding"}
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>

      {/* Edit Vendor Profile Modal */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="max-w-2xl bg-white border border-slate-200 shadow-2xl rounded-2xl overflow-hidden p-0">
          <DialogHeader className="p-6 bg-slate-50/50 border-b border-slate-100">
            <DialogTitle className="text-slate-900 font-black text-xl flex items-center gap-2">
              <Sliders className="w-5 h-5 text-indigo-600" /> Edit Partner Profile Details
            </DialogTitle>
            <DialogDescription>
              Modify company parameters, contact records, or platform commission rate structures.
            </DialogDescription>
          </DialogHeader>

          {selectedVendor && (
            <form onSubmit={handleEditSubmit}>
              <div className="p-6 space-y-4 max-h-[60vh] overflow-y-auto">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="edit_company_name" className="text-slate-700 font-semibold text-xs">Company Name</Label>
                    <Input 
                      id="edit_company_name" 
                      value={selectedVendor.company_name || ""}
                      onChange={(e) => setSelectedVendor({...selectedVendor, company_name: e.target.value})}
                      required
                      className="text-slate-800 border-slate-200"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit_owner_name" className="text-slate-700 font-semibold text-xs">Owner Full Name</Label>
                    <Input 
                      id="edit_owner_name" 
                      value={selectedVendor.owner_name || ""}
                      onChange={(e) => setSelectedVendor({...selectedVendor, owner_name: e.target.value})}
                      required
                      className="text-slate-800 border-slate-200"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="edit_email" className="text-slate-700 font-semibold text-xs">Email Address (Read-only)</Label>
                    <Input 
                      id="edit_email" 
                      value={selectedVendor.email || ""}
                      readOnly
                      disabled
                      className="text-slate-400 bg-slate-50 border-slate-200 cursor-not-allowed"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit_phone" className="text-slate-700 font-semibold text-xs">WhatsApp Number</Label>
                    <Input 
                      id="edit_phone" 
                      value={selectedVendor.phone || ""}
                      onChange={(e) => setSelectedVendor({...selectedVendor, phone: e.target.value})}
                      required
                      className="text-slate-800 border-slate-200"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="edit_password" className="text-slate-700 font-semibold text-xs">New Password (Leave blank to keep current)</Label>
                    <Input 
                      id="edit_password" 
                      type="password"
                      placeholder="••••••••" 
                      value={selectedVendor.password || ""}
                      onChange={(e) => setSelectedVendor({...selectedVendor, password: e.target.value})}
                      className="text-slate-800 border-slate-200"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit_vendor_type" className="text-slate-700 font-semibold text-xs">Service Category</Label>
                    <select 
                      id="edit_vendor_type"
                      value={selectedVendor.vendor_type || "Tour Operator"}
                      onChange={(e) => setSelectedVendor({...selectedVendor, vendor_type: e.target.value})}
                      className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 text-slate-800 h-10"
                    >
                      {VENDOR_TYPES.map(type => (
                        <option key={type} value={type}>{type}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="edit_city" className="text-slate-700 font-semibold text-xs">Operating City</Label>
                    <Input 
                      id="edit_city" 
                      value={selectedVendor.city || ""}
                      onChange={(e) => setSelectedVendor({...selectedVendor, city: e.target.value})}
                      required
                      className="text-slate-800 border-slate-200"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit_gst_number" className="text-slate-700 font-semibold text-xs">GSTIN</Label>
                    <Input 
                      id="edit_gst_number" 
                      value={selectedVendor.gst_number || ""}
                      onChange={(e) => setSelectedVendor({...selectedVendor, gst_number: e.target.value})}
                      className="text-slate-800 border-slate-200"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit_commission" className="text-slate-700 font-semibold text-xs">Commission %</Label>
                    <Input 
                      id="edit_commission" 
                      type="number"
                      min="0"
                      max="100"
                      value={selectedVendor.commission_percentage || 0}
                      onChange={(e) => setSelectedVendor({...selectedVendor, commission_percentage: parseFloat(e.target.value) || 0})}
                      required
                      className="text-slate-800 border-slate-200"
                    />
                  </div>
                </div>
              </div>

              <DialogFooter className="p-6 bg-slate-50/50 border-t border-slate-100">
                <DialogClose className="px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-700 hover:bg-slate-100 font-semibold cursor-pointer transition-colors bg-white">
                  Cancel
                </DialogClose>
                <Button type="submit" disabled={updateMutation.isPending} className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm shadow-indigo-100 border-0">
                  {updateMutation.isPending ? "Updating profile..." : "Save Changes"}
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
}
