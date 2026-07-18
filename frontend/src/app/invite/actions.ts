"use server";

import { createClient } from "@supabase/supabase-js";
import { randomBytes } from "crypto";

// Admin client uses service_role key to bypass RLS and create records securely
function getAdminClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;
  if (!serviceKey || serviceKey === "YOUR_SERVICE_ROLE_KEY_HERE") {
    throw new Error("SUPABASE_SERVICE_ROLE_KEY is not set.");
  }
  return createClient(url, serviceKey, {
    auth: { autoRefreshToken: false, persistSession: false }
  });
}

/**
 * Creates an invitation for a new user (e.g., Doctor or Staff)
 */
export async function createInvitation(params: {
  tenantId: string;
  email: string;
  role: string;
  metadata: any;
}) {
  try {
    const adminClient = getAdminClient();

    // 1. Check if user already exists
    const { data: existingUser } = await adminClient
      .from("users")
      .select("id")
      .eq("email", params.email)
      .maybeSingle();

    if (existingUser) {
      return { error: "A user with this email already exists." };
    }

    // 2. Check if a pending invitation already exists
    const { data: existingInvite } = await adminClient
      .from("invitations")
      .select("id")
      .eq("email", params.email)
      .eq("status", "pending")
      .maybeSingle();

    if (existingInvite) {
      return { error: "An invitation is already pending for this email." };
    }

    // 3. Generate a secure random token
    const token = randomBytes(32).toString("hex");

    // 4. Save the invitation
    const { data: invitation, error } = await adminClient
      .from("invitations")
      .insert({
        tenant_id: params.tenantId,
        email: params.email,
        role: params.role,
        metadata: params.metadata,
        token: token,
        status: "pending"
      })
      .select()
      .single();

    if (error || !invitation) {
      console.error("Error creating invitation:", error);
      return { error: "Failed to create invitation." };
    }

    return { success: true, token: invitation.token };
  } catch (error: any) {
    console.error("createInvitation error:", error);
    return { error: error.message || "An unexpected error occurred." };
  }
}

/**
 * Retrieves an invitation by its token
 */
export async function getInvitationByToken(token: string) {
  try {
    const adminClient = getAdminClient();
    const { data: invitation, error } = await adminClient
      .from("invitations")
      .select("*, tenants(hospital_name)")
      .eq("token", token)
      .eq("status", "pending")
      .maybeSingle();

    if (error || !invitation) {
      return { error: "Invalid or expired invitation." };
    }

    return { invitation };
  } catch (error: any) {
    return { error: "Failed to fetch invitation." };
  }
}

/**
 * Common logic to complete an invitation (called after auth)
 */
async function completeInvitationFlow(adminClient: any, userId: string, invitation: any) {
  // 1. Create the user profile
  const { error: userError } = await adminClient
    .from("users")
    .upsert({
      id: userId,
      tenant_id: invitation.tenant_id,
      name: invitation.metadata.name,
      email: invitation.email,
      role: invitation.role,
      roles: [invitation.role],
      active_role: invitation.role,
    });

  if (userError) throw userError;

  // 2. Create the role-specific profile (Doctor)
  if (invitation.role === "doctor") {
    const { error: doctorError } = await adminClient
      .from("doctors")
      .insert({
        tenant_id: invitation.tenant_id,
        name: invitation.metadata.name,
        specialization: invitation.metadata.specialization,
        experience_years: invitation.metadata.experience || 0,
        consultation_fee: invitation.metadata.fee || 0,
        qualifications: ["MBBS"],
        languages: ["English"],
        availability_schedule: { "monday": ["09:00-17:00"] },
        is_active: true,
        whatsapp_number: invitation.metadata.whatsapp_number || null,
      });
      
    if (doctorError) throw doctorError;
  }

  // 3. Mark invitation as accepted
  await adminClient
    .from("invitations")
    .update({ status: "accepted" })
    .eq("id", invitation.id);
}

/**
 * Accepts an invitation using Email/Password authentication
 */
export async function acceptInvitationWithEmail(token: string, password: string) {
  try {
    const adminClient = getAdminClient();
    
    // 1. Verify invitation
    const { data: invitation, error: inviteError } = await adminClient
      .from("invitations")
      .select("*")
      .eq("token", token)
      .eq("status", "pending")
      .maybeSingle();

    if (inviteError || !invitation) {
      return { error: "Invalid or expired invitation." };
    }

    // 2. Create Auth User without email verification required
    const { data: authData, error: authError } = await adminClient.auth.admin.createUser({
      email: invitation.email,
      password: password,
      email_confirm: true,
      user_metadata: {
        full_name: invitation.metadata.name,
        role: invitation.role,
        roles: [invitation.role],
        activeRole: invitation.role
      }
    });

    if (authError || !authData.user) {
      return { error: authError?.message || "Failed to create authentication user." };
    }

    const userId = authData.user.id;

    // 3. Complete the flow
    await completeInvitationFlow(adminClient, userId, invitation);

    return { success: true };
  } catch (error: any) {
    console.error("acceptInvitationWithEmail error:", error);
    return { error: error.message || "An unexpected error occurred." };
  }
}

/**
 * Accepts an invitation using Google OAuth (called from callback page)
 */
export async function acceptInvitationWithGoogle(token: string, userId: string, userEmail: string) {
  try {
    const adminClient = getAdminClient();
    
    // 1. Verify invitation
    const { data: invitation, error: inviteError } = await adminClient
      .from("invitations")
      .select("*")
      .eq("token", token)
      .eq("status", "pending")
      .maybeSingle();

    if (inviteError || !invitation) {
      return { error: "Invalid or expired invitation." };
    }

    // 2. Verify the Google user matches the invited email
    if (userEmail.toLowerCase() !== invitation.email.toLowerCase()) {
      return { error: "The authenticated email does not match the invitation email." };
    }

    // 3. Update Auth User metadata
    await adminClient.auth.admin.updateUserById(userId, {
      user_metadata: { 
        full_name: invitation.metadata.name, 
        role: invitation.role,
        roles: [invitation.role],
        activeRole: invitation.role
      }
    });

    // 4. Complete the flow
    await completeInvitationFlow(adminClient, userId, invitation);

    return { success: true };
  } catch (error: any) {
    console.error("acceptInvitationWithGoogle error:", error);
    return { error: error.message || "An unexpected error occurred." };
  }
}
