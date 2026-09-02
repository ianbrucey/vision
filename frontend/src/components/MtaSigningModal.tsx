"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { X, Loader2 } from "lucide-react";
import { signMyMta, type MtaAgreement } from "@/lib/api";

interface MtaSigningModalProps {
  open: boolean;
  previewUrl: string;
  previewName: string;
  businessName: string;
  onClose: () => void;
  onSigned: (agreement: MtaAgreement) => void;
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function MtaSigningModal({
  open,
  previewUrl,
  previewName,
  businessName,
  onClose,
  onSigned,
}: MtaSigningModalProps) {
  const [signedName, setSignedName] = useState("");
  const [signedTitle, setSignedTitle] = useState("");
  const [consent, setConsent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const previousFocus = useRef<HTMLElement | null>(null);

  /* ---- scroll lock + focus restore + Escape close ---- */

  useEffect(() => {
    if (!open) return;
    previousFocus.current = document.activeElement as HTMLElement;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKey);
      previousFocus.current?.focus?.();
    };
  }, [open, onClose]);

  const reset = useCallback(() => {
    setSignedName("");
    setSignedTitle("");
    setConsent(false);
    setError(null);
  }, []);

  useEffect(() => {
    if (open) reset();
  }, [open, reset]);

  if (!open) return null;

  const canSubmit = signedName.trim().length >= 2 && signedTitle.trim().length >= 2 && consent && !loading;

  const handleSubmit = () => {
    if (!canSubmit) return;
    setLoading(true);
    setError(null);
    signMyMta({ signed_name: signedName.trim(), signed_title: signedTitle.trim(), consent })
      .then((res) => {
        reset();
        onSigned(res.agreement);
      })
      .catch((err: Error) => {
        setError(err.message || "Signing failed. Please try again.");
      })
      .finally(() => setLoading(false));
  };

  return (
    <div className="fixed inset-0 z-50 bg-surface-0 flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-30 bg-surface-0/80 backdrop-blur-sm border-b border-border">
        <div className="max-w-5xl mx-auto flex items-center justify-between h-14 px-4">
          <div>
            <h2 className="text-base font-semibold text-text-primary">Master Teaming Agreement</h2>
            <p className="text-xs text-text-secondary">{businessName} — Justice Quest LLC</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-surface-2 text-text-disabled"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>
      </header>

      {/* Content */}
      <div className="max-w-5xl w-full mx-auto px-4 py-6 flex-1 overflow-y-auto">
        {/* PDF preview */}
        <iframe
          src={previewUrl}
          title={previewName}
          className="w-full h-[62vh] rounded-lg border border-border bg-surface-1"
        />
        <p className="text-[10px] text-text-disabled mt-1.5 mb-4">
          Preview — no signature has been captured. You are reviewing the document you will be asked to sign.
        </p>

        {/* Error */}
        {error && (
          <div className="mb-4 px-3 py-2 text-xs text-danger bg-danger-bg rounded-lg">
            {error}
          </div>
        )}

        {/* Form */}
        <div className="space-y-4 pb-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-text-secondary">
                Signed name <span className="text-text-disabled">(legal name of authorized signatory)</span>
              </label>
              <input
                type="text"
                value={signedName}
                onChange={(e) => setSignedName(e.target.value)}
                className="mt-1 w-full px-3 py-2.5 text-sm bg-surface-1 border border-border rounded-lg text-text-primary outline-none focus:border-brand"
                placeholder="Jane Doe"
                autoComplete="name"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-text-secondary">Title</label>
              <input
                type="text"
                value={signedTitle}
                onChange={(e) => setSignedTitle(e.target.value)}
                className="mt-1 w-full px-3 py-2.5 text-sm bg-surface-1 border border-border rounded-lg text-text-primary outline-none focus:border-brand"
                placeholder="Owner"
                autoComplete="organization-title"
              />
            </div>
          </div>

          <label className="flex items-start gap-3 cursor-pointer pt-1">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="size-4 rounded-sm border-border-strong bg-surface-2 text-brand mt-0.5"
            />
            <span className="text-xs text-text-secondary leading-relaxed">
              I have reviewed this Master Teaming Agreement, understand its terms, and agree to be legally bound.
              My typed name constitutes my electronic signature (E-SIGN Act 15 U.S.C. §7001; Georgia UETA O.C.G.A. §10-12).
            </span>
          </label>

          <div className="flex justify-end gap-3 pt-2">
            <button
              onClick={onClose}
              className="px-4 py-2.5 text-sm font-medium text-text-secondary border border-border rounded-lg hover:bg-surface-2 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={!canSubmit}
              className="bg-brand hover:bg-brand-hover text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-2"
            >
              {loading && <Loader2 size={14} className="animate-spin" />}
              Sign & Submit
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
