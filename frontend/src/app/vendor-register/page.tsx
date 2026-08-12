"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, CheckCircle2 } from "lucide-react";
import { registerVendor } from "@/lib/api";

const VENDOR_TYPES = [
  { value: "service", label: "Service Provider", desc: "Construction, IT, consulting, facilities, etc." },
  { value: "manufacturer", label: "Manufacturer / Supplier", desc: "Product manufacturer, equipment supplier, reseller" },
  { value: "individual", label: "Individual / Sole Proprietor", desc: "Independent contractor, consultant, 1099 worker" },
];

export default function VendorRegisterPage() {
  const router = useRouter();
  const [step, setStep] = useState<"form" | "success">("form");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [vendorType, setVendorType] = useState("service");
  const [phone, setPhone] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await registerVendor({
        username: username.trim(),
        password,
        email: email.trim() || undefined,
        business_name: businessName.trim(),
        vendor_type: vendorType,
        phone: phone.trim() || undefined,
      });
      setStep("success");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  if (step === "success") {
    return (
      <main className="min-h-dvh bg-surface-0 text-text-primary flex items-center justify-center">
        <div className="max-w-sm w-full mx-4 text-center">
          <CheckCircle2 size={48} className="text-success mx-auto mb-4" />
          <h1 className="text-xl font-semibold mb-2">Registration Complete</h1>
          <p className="text-sm text-text-secondary mb-6">
            Your vendor account has been created. Sign in to access your portal.
          </p>
          <button
            onClick={() => router.push("/login")}
            className="bg-brand hover:bg-brand-hover text-white px-6 py-3 rounded-lg text-sm font-medium transition-colors"
          >
            Sign In
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-dvh bg-surface-0 text-text-primary flex items-center justify-center">
      <div className="max-w-md w-full mx-4">
        <h1 className="text-xl font-semibold mb-1">Register as Vendor</h1>
        <p className="text-sm text-text-secondary mb-6">
          Join our subcontractor network to receive quote requests for federal opportunities.
        </p>

        {error && (
          <div className="mb-4 px-3 py-2 text-xs text-danger bg-danger-bg rounded-lg">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block">
            <span className="text-xs text-text-secondary">Business Name *</span>
            <input
              type="text"
              value={businessName}
              onChange={e => setBusinessName(e.target.value)}
              required
              className="mt-1 w-full px-3 py-2.5 text-sm bg-surface-1 border border-border rounded-lg text-text-primary outline-none focus:border-brand"
              placeholder="Your company name"
            />
          </label>

          <label className="block">
            <span className="text-xs text-text-secondary">Vendor Type *</span>
            <div className="mt-1 grid grid-cols-1 gap-2">
              {VENDOR_TYPES.map((vt) => (
                <label
                  key={vt.value}
                  className={`flex items-start gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                    vendorType === vt.value
                      ? "border-brand bg-brand-bg/30"
                      : "border-border hover:border-border-strong"
                  }`}
                >
                  <input
                    type="radio"
                    name="vendorType"
                    value={vt.value}
                    checked={vendorType === vt.value}
                    onChange={e => setVendorType(e.target.value)}
                    className="mt-0.5"
                  />
                  <div>
                    <p className="text-sm font-medium text-text-primary">{vt.label}</p>
                    <p className="text-xs text-text-disabled">{vt.desc}</p>
                  </div>
                </label>
              ))}
            </div>
          </label>

          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-xs text-text-secondary">Username *</span>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
                className="mt-1 w-full px-3 py-2.5 text-sm bg-surface-1 border border-border rounded-lg text-text-primary outline-none focus:border-brand"
              />
            </label>
            <label className="block">
              <span className="text-xs text-text-secondary">Password *</span>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                minLength={6}
                className="mt-1 w-full px-3 py-2.5 text-sm bg-surface-1 border border-border rounded-lg text-text-primary outline-none focus:border-brand"
              />
            </label>
          </div>

          <label className="block">
            <span className="text-xs text-text-secondary">Email</span>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="mt-1 w-full px-3 py-2.5 text-sm bg-surface-1 border border-border rounded-lg text-text-primary outline-none focus:border-brand"
              placeholder="info@yourcompany.com"
            />
          </label>

          <label className="block">
            <span className="text-xs text-text-secondary">Phone</span>
            <input
              type="text"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              className="mt-1 w-full px-3 py-2.5 text-sm bg-surface-1 border border-border rounded-lg text-text-primary outline-none focus:border-brand"
              placeholder="(555) 000-0000"
            />
          </label>

          <button
            type="submit"
            disabled={loading || !businessName.trim() || !username.trim() || password.length < 6}
            className="w-full bg-brand hover:bg-brand-hover text-white py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
          >
            {loading ? <Loader2 size={16} className="animate-spin inline mr-2" /> : null}
            {loading ? "Creating Account..." : "Register"}
          </button>

          <p className="text-xs text-text-disabled text-center">
            Already have an account?{" "}
            <button type="button" onClick={() => router.push("/login")} className="text-brand hover:underline">
              Sign in
            </button>
          </p>
        </form>
      </div>
    </main>
  );
}
