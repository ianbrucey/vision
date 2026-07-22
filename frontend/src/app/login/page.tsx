"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { login } from "@/lib/auth";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
      router.replace("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Invalid credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-dvh bg-surface-0 text-text-primary flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-brand">Vision AI Systems</h1>
          <p className="text-text-secondary mt-2 text-sm">By Justice Quest</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-surface-1 rounded-xl border border-border shadow-sm p-6 space-y-4">
          <h2 className="text-lg font-semibold text-text-primary">Sign In</h2>

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
              placeholder="Enter your username"
              required
              autoFocus
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
              placeholder="Enter your password"
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
            {loading ? "Signing in..." : "Sign In"}
          </button>

          <p className="text-center text-sm text-text-secondary">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="text-info hover:text-brand underline-offset-2 hover:underline transition-colors duration-150">
              Register
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
