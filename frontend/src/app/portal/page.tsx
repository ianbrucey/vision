"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Building2, FileText, Clock, AlertCircle, CheckCircle2 } from "lucide-react";
import { useAuth } from "@/components/AuthProvider";
import { getMyVendorProfile, getMyMtaStatus, type VendorProfile, type MtaStatusResponse, type MtaAgreement } from "@/lib/api";
import MtaSigningModal from "@/components/MtaSigningModal";
import DocumentPreviewModal from "@/components/DocumentPreviewModal";

export default function PortalDashboard() {
  const { user, ready, logout } = useAuth();
  const router = useRouter();
  const [profile, setProfile] = useState<VendorProfile | null>(null);
  const [mtaStatus, setMtaStatus] = useState<MtaStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [signingOpen, setSigningOpen] = useState(false);
  const [showSignedDoc, setShowSignedDoc] = useState(false);

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
      .catch(() => {});
    getMyMtaStatus()
      .then(setMtaStatus)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user]);

  const handleSigned = (agreement: MtaAgreement) => {
    setMtaStatus({ signed: true, agreement, document_id: agreement.document_id });
    setSigningOpen(false);
  };

  if (!ready || !user) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-text-disabled" size={24} />
      </div>
    );
  }

  const mtaSigned = mtaStatus?.signed === true;

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

        {/* MTA status banner */}
        {!loading && mtaStatus && (
          mtaSigned ? (
            <div className="bg-success-bg border border-success/20 rounded-lg p-3 md:p-4 flex gap-2 md:gap-3 mb-6">
              <CheckCircle2 className="text-success shrink-0 mt-0.5" size={18} />
              <div className="flex-1 flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-success">Master Teaming Agreement active</p>
                  <p className="text-xs md:text-sm text-text-secondary mt-0.5">
                    Signed {mtaStatus.agreement?.executed_at ? new Date(mtaStatus.agreement.executed_at).toLocaleDateString() : ""} by {mtaStatus.agreement?.signed_name}, {mtaStatus.agreement?.signed_title}.
                  </p>
                </div>
                <button
                  onClick={() => setShowSignedDoc(true)}
                  className="bg-brand hover:bg-brand-hover text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shrink-0"
                >
                  View signed agreement
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-warning-bg border border-warning/20 rounded-lg p-3 md:p-4 flex gap-2 md:gap-3 mb-6">
              <AlertCircle className="text-warning shrink-0 mt-0.5" size={18} />
              <div className="flex-1 flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-warning">Master Teaming Agreement required</p>
                  <p className="text-xs md:text-sm text-text-secondary mt-0.5">
                    Please review and sign your Master Teaming Agreement to activate your account and receive quote requests.
                  </p>
                </div>
                <button
                  onClick={() => setSigningOpen(true)}
                  className="bg-brand hover:bg-brand-hover text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shrink-0"
                >
                  Review & Sign
                </button>
              </div>
            </div>
          )
        )}

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

      {/* MTA signing modal (unsigned state) */}
      {mtaStatus?.preview_url && (
        <MtaSigningModal
          open={signingOpen}
          previewUrl={mtaStatus.preview_url}
          previewName={mtaStatus.preview_name || "Master Teaming Agreement.pdf"}
          businessName={profile?.business_name || user.username}
          onClose={() => setSigningOpen(false)}
          onSigned={handleSigned}
        />
      )}

      {/* Signed PDF viewer */}
      {mtaStatus?.document_id && (
        <DocumentPreviewModal
          open={showSignedDoc}
          docId={mtaStatus.document_id}
          docName="Master Teaming Agreement"
          onClose={() => setShowSignedDoc(false)}
        />
      )}
    </main>
  );
}
