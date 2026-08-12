"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { FileSearch, Users, FileText, TrendingUp } from "lucide-react";

export default function LandingPage() {
  const { user } = useAuth();
  const router = useRouter();

  return (
    <main className="min-h-dvh bg-surface-0 text-text-primary flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-30 bg-surface-0/80 backdrop-blur-sm border-b border-border">
        <div className="max-w-5xl mx-auto flex items-center justify-between h-14 px-4">
          <h1 className="text-lg font-semibold tracking-tight">Vision</h1>
          <div className="flex items-center gap-3">
            {user ? (
              <button
                onClick={() => router.push("/solicitations")}
                className="bg-brand hover:bg-brand-hover text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                Dashboard
              </button>
            ) : (
              <>
                <button
                  onClick={() => router.push("/vendor-register")}
                  className="text-text-secondary hover:text-brand px-3 py-2 rounded-lg text-sm font-medium transition-colors"
                >
                  Register as Vendor
                </button>
                <button
                  onClick={() => router.push("/login")}
                  className="bg-brand hover:bg-brand-hover text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                >
                  Sign In
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-3xl mx-auto px-4 py-20 text-center">
        <h2 className="text-3xl font-bold tracking-tight mb-4">
          Government Contracting,<br />Powered by AI
        </h2>
        <p className="text-text-secondary max-w-xl mx-auto mb-8 leading-relaxed">
          Find federal opportunities, match with qualified vendors, automate
          outreach, and fill government forms — all from one platform.
        </p>
        {user ? (
          <button
            onClick={() => router.push("/solicitations")}
            className="bg-brand hover:bg-brand-hover text-white px-6 py-3 rounded-lg text-sm font-medium transition-colors"
          >
            Go to Dashboard
          </button>
        ) : (
          <button
            onClick={() => router.push("/login")}
            className="bg-brand hover:bg-brand-hover text-white px-6 py-3 rounded-lg text-sm font-medium transition-colors"
          >
            Get Started
          </button>
        )}
      </section>

      {/* Features */}
      <section className="max-w-5xl mx-auto px-4 pb-20">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <FeatureCard
            icon={<FileSearch size={24} />}
            title="Find Opportunities"
            description="Search SAM.gov, Acquisition Gateway forecasts, and your own databank exports for viable contracts."
          />
          <FeatureCard
            icon={<Users size={24} />}
            title="Match Vendors"
            description="Auto-match 5.5M+ small businesses to solicitations by NAICS, set-aside, and capabilities."
          />
          <FeatureCard
            icon={<FileText size={24} />}
            title="Fill Forms"
            description="Auto-populate SF-1449s, price schedules, and amendment forms with AI-powered precision."
          />
          <FeatureCard
            icon={<TrendingUp size={24} />}
            title="Track Pipeline"
            description="Triage, score, and track every opportunity from discovery through submission."
          />
        </div>
      </section>
    </main>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="bg-surface-1 border border-border rounded-lg p-6 text-center">
      <div className="text-brand mb-3 flex justify-center">{icon}</div>
      <h3 className="text-sm font-semibold mb-2">{title}</h3>
      <p className="text-xs text-text-secondary leading-relaxed">{description}</p>
    </div>
  );
}
