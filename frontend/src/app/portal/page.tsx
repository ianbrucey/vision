"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Building2, FileText, Clock } from "lucide-react";
import { useAuth } from "@/components/AuthProvider";
import { getMyVendorProfile, type VendorProfile } from "@/lib/api";

export default function PortalDashboard() {
  const { user, ready, logout } = useAuth();
  const router = useRouter();
  const [profile, setProfile] = useState<VendorProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (ready && !user) {
      router.replace("/login");
      return;
    }
    if (ready && user?.role !== "vendor") {
      router.replace("/solicitations");
      return;
    }
  }, [user, ready, router]);

  useEffect(() => {
    if (!user) return;
    getMyVendorProfile()
      .then(setProfile)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user]);

  if (!ready || !user) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-text-disabled" size={24} />
      </div>
    );
  }

  return (
    <main className="min-h-dvh bg-surface-0 text-text-primary">
      {/* Header */}
      <header className="sticky top-0 z-30 bg-surface-0/80 backdrop-blur-sm border-b border-border">
        <div className="max-w-5xl mx-auto flex items-center justify-between h-14 px-4">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold tracking-tight">Vision</h1>
            <span className="text-xs text-text-disabled border-l border-border pl-3">Vendor Portal</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-text-secondary">{profile?.business_name || user.username}</span>
            <button onClick={logout} className="text-xs text-text-disabled hover:text-text-secondary">Sign out</button>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        <h2 className="text-lg font-semibold mb-1">
          {loading ? "Loading..." : `Welcome, ${profile?.business_name || user.username}`}
        </h2>
        <p className="text-sm text-text-secondary mb-8">
          {profile
            ? `${profile.vendor_type} · Status: ${profile.status}`
            : "Complete your profile to start receiving quote requests."}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-surface-1 border border-border rounded-lg p-6">
            <Building2 size={24} className="text-brand mb-3" />
            <h3 className="text-sm font-semibold mb-1">Profile</h3>
            <p className="text-xs text-text-secondary">
              {profile ? "Manage your business profile, capabilities, and compliance documents." : "Create your vendor profile."}
            </p>
          </div>
          <div className="bg-surface-1 border border-border rounded-lg p-6 opacity-50">
            <FileText size={24} className="text-text-disabled mb-3" />
            <h3 className="text-sm font-semibold mb-1">Quote Requests</h3>
            <p className="text-xs text-text-secondary">View and respond to quote requests from the prime.</p>
          </div>
          <div className="bg-surface-1 border border-border rounded-lg p-6 opacity-50">
            <Clock size={24} className="text-text-disabled mb-3" />
            <h3 className="text-sm font-semibold mb-1">History</h3>
            <p className="text-xs text-text-secondary">Track submitted quotes and awarded contracts.</p>
          </div>
        </div>
      </div>
    </main>
  );
}
