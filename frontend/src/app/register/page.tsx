"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { register } from "@/lib/auth";

export default function RegisterPage() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }
    setLoading(true);
    try {
      await register(username, password, email || undefined);
      router.replace("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-dvh bg-surface-0 text-text-primary flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-brand">Vision</h1>
          <p className="text-text-secondary mt-2 text-sm">War Room Agent</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-surface-1 rounded-xl border border-border shadow-sm p-6 space-y-4">
          <h2 className="text-lg font-semibold text-text-primary">Create Account</h2>

          {error && (
            <div className="bg-danger-bg border border-danger/20 text-danger text-sm rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <div>
            <label className="block mb-1.5 text-sm font-medium text-text-secondary">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2 text-sm text-text-primary
                         bg-surface-2 border border-border rounded-sm
                         placeholder:text-text-disabled
                         focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                         transition-colors duration-150"
              placeholder="Choose a username"
              required
              autoFocus
            />
          </div>

          <div>
            <label className="block mb-1.5 text-sm font-medium text-text-secondary">
              Email <span className="text-text-disabled">(optional)</span>
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 text-sm text-text-primary
                         bg-surface-2 border border-border rounded-sm
                         placeholder:text-text-disabled
                         focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                         transition-colors duration-150"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label className="block mb-1.5 text-sm font-medium text-text-secondary">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 text-sm text-text-primary
                         bg-surface-2 border border-border rounded-sm
                         placeholder:text-text-disabled
                         focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                         transition-colors duration-150"
              placeholder="At least 6 characters"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full inline-flex items-center justify-center gap-2
                       bg-brand text-white border border-brand
                       hover:bg-brand-hover active:bg-brand-active
                       disabled:opacity-50 disabled:cursor-not-allowed
                       px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-150"
          >
            {loading && <Loader2 size={16} className="animate-spin" />}
            {loading ? "Creating..." : "Create Account"}
          </button>

          <p className="text-center text-sm text-text-secondary">
            Already have an account?{" "}
            <Link href="/login" className="text-info hover:text-brand underline-offset-2 hover:underline transition-colors duration-150">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
