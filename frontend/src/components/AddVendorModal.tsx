"use client";

import { useState } from "react";
import { X, Loader2 } from "lucide-react";
import { createVendor, attachVendorMatch, type CreatedVendor } from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface AddVendorModalProps {
  open: boolean;
  onClose: () => void;
  /** If set, the newly-created vendor is also attached to this solicitation's
   * vendor_matches list (T7). Omit for the standalone VendorsTab flow. */
  solicitationId?: number;
  onCreated: (vendor: CreatedVendor) => void;
}

const SET_ASIDE_FIELDS: { key: keyof typeof INITIAL_FLAGS; label: string }[] = [
  { key: "is_small_business", label: "Small Business" },
  { key: "is_sdvosb", label: "SDVOSB" },
  { key: "is_woman_owned", label: "Woman-Owned" },
  { key: "is_veteran_owned", label: "Veteran-Owned" },
  { key: "is_hubzone", label: "HUBZone" },
  { key: "is_8a", label: "8(a)" },
];

const INITIAL_FLAGS = {
  is_small_business: false,
  is_sdvosb: false,
  is_woman_owned: false,
  is_veteran_owned: false,
  is_hubzone: false,
  is_8a: false,
};

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function AddVendorModal({ open, onClose, solicitationId, onCreated }: AddVendorModalProps) {
  const [vendorName, setVendorName] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [website, setWebsite] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [naics, setNaics] = useState("");
  const [flags, setFlags] = useState({ ...INITIAL_FLAGS });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  if (!open) return null;

  const reset = () => {
    setVendorName(""); setContactName(""); setContactEmail(""); setContactPhone("");
    setWebsite(""); setCity(""); setState(""); setNaics("");
    setFlags({ ...INITIAL_FLAGS });
    setError("");
  };

  const handleClose = () => {
    if (saving) return;
    reset();
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!vendorName.trim() || saving) return;
    setSaving(true);
    setError("");
    try {
      const vendor = await createVendor({
        vendor_name: vendorName.trim(),
        contact_name: contactName.trim() || undefined,
        contact_email: contactEmail.trim() || undefined,
        contact_phone: contactPhone.trim() || undefined,
        website: website.trim() || undefined,
        city: city.trim() || undefined,
        state: state.trim() || undefined,
        naics_code_primary: naics.trim() || undefined,
        ...flags,
      });
      if (solicitationId) {
        await attachVendorMatch(solicitationId, vendor.id);
      }
      onCreated(vendor);
      reset();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create vendor");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 flex items-end sm:items-center justify-center p-0 sm:p-4"
      onClick={(e) => { if (e.target === e.currentTarget) handleClose(); }}
    >
      <div className="bg-surface-1 border border-border rounded-t-xl sm:rounded-xl shadow-md
                       w-full sm:min-w-[440px] sm:max-w-[560px] max-h-[90dvh] sm:max-h-[85vh]
                       overflow-y-auto p-5 sm:p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text-primary">Add Vendor</h2>
          <button
            onClick={handleClose}
            className="min-h-[44px] min-w-[44px] sm:size-8 rounded-sm inline-flex items-center justify-center
                       text-text-secondary hover:bg-surface-2 hover:text-text-primary transition-colors"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {error && (
            <p className="text-xs text-danger bg-danger-bg rounded px-2.5 py-1.5">{error}</p>
          )}

          <div className="flex flex-col gap-1.5">
            <label htmlFor="vendor_name" className="text-sm font-medium text-text-secondary">
              Vendor Name *
            </label>
            <input
              id="vendor_name"
              type="text"
              value={vendorName}
              onChange={(e) => setVendorName(e.target.value)}
              required
              autoFocus
              className="w-full h-9 px-2.5 rounded border border-border bg-surface-0
                         text-sm text-text-primary placeholder:text-text-disabled
                         focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand/20"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Contact Name" value={contactName} onChange={setContactName} />
            <Field label="Contact Email" value={contactEmail} onChange={setContactEmail} type="email" />
            <Field label="Contact Phone" value={contactPhone} onChange={setContactPhone} />
            <Field label="Website" value={website} onChange={setWebsite} />
            <Field label="City" value={city} onChange={setCity} />
            <Field label="State" value={state} onChange={(v) => setState(v.toUpperCase())} maxLength={2} />
            <Field label="NAICS Code" value={naics} onChange={setNaics} />
          </div>

          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium text-text-secondary">Set-aside Status</span>
            <div className="flex flex-wrap gap-3">
              {SET_ASIDE_FIELDS.map((f) => (
                <label key={f.key} className="flex items-center gap-1.5 text-xs text-text-secondary cursor-pointer">
                  <input
                    type="checkbox"
                    checked={flags[f.key]}
                    onChange={(e) => setFlags((prev) => ({ ...prev, [f.key]: e.target.checked }))}
                    className="rounded border-border"
                  />
                  {f.label}
                </label>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={handleClose}
              disabled={saving}
              className="text-sm text-text-secondary hover:text-text-primary px-3 py-1.5"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!vendorName.trim() || saving}
              className="inline-flex items-center gap-1.5 h-9 px-4 rounded bg-brand text-white text-sm font-medium
                         hover:bg-brand-emphasis transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving && <Loader2 size={14} className="animate-spin" />}
              {saving ? "Saving..." : "Add Vendor"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Field                                                              */
/* ------------------------------------------------------------------ */

function Field({
  label, value, onChange, type = "text", maxLength,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  maxLength?: number;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-text-secondary">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        maxLength={maxLength}
        className="w-full h-9 px-2.5 rounded border border-border bg-surface-0
                   text-sm text-text-primary placeholder:text-text-disabled
                   focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand/20"
      />
    </div>
  );
}
