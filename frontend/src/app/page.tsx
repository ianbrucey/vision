"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { FileSearch, Users, FileText, TrendingUp, Landmark, Handshake } from "lucide-react";

export default function LandingPage() {
  const { user } = useAuth();
  const router = useRouter();

  return (
    <main className="min-h-dvh bg-gsc-navy text-white flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-30 bg-gsc-navy/80 backdrop-blur-sm border-b-1 border-white">
        <div className="max-w-5xl mx-auto flex items-center justify-between h-20 px-4">
          <img
            src="/images/GSC-logo-short.png"
            alt="Gov Services Connect"
            className="h-12.5 w-auto"
          />
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
                  className="text-gsc-body hover:text-brand px-3 py-2 rounded-lg text-sm font-medium transition-colors"
                >
                  Join Our Network
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

      {/* Hero — copy left, logo right. Full viewport on all breakpoints. */}
      <section className="max-w-5xl mx-auto px-4 flex items-center min-h-[calc(100dvh-4rem)]">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center w-full">
          <div className="text-center lg:text-left">
            <h1 className="text-3xl font-bold tracking-tight mb-4">
              We grow small businesses with consistent government work.
            </h1>
            <p className="text-gsc-body max-w-xl mx-auto lg:mx-0 mb-8 leading-relaxed">
              We find the work that government hasn&apos;t filled — the
              contracts and services federal, state, and local agencies need
              delivered — and we bring it to you. Join our network, get
              matched to opportunities you qualify for, and deliver what you
              do best. We handle the registration, the compliance, the
              proposals, and the invoicing, so your business grows on steady
              government work instead of chasing one-off jobs.
            </p>
            {user ? (
              <button
                onClick={() => router.push("/solicitations")}
                className="bg-brand hover:bg-brand-hover text-white px-6 py-3 rounded-lg text-sm font-medium transition-colors"
              >
                Go to Dashboard
              </button>
            ) : (
              <div className="flex items-center justify-center lg:justify-start gap-3">
                <button
                  onClick={() => router.push("/login")}
                  className="bg-brand hover:bg-brand-hover text-white px-6 py-3 rounded-lg text-sm font-medium transition-colors"
                >
                  Login
                </button>
                <button
                  onClick={() => router.push("/vendor-register")}
                  className="border border-gsc-navy-line text-gsc-body hover:text-brand hover:border-brand px-6 py-3 rounded-lg text-sm font-medium transition-colors"
                >
                  Join Our Network
                </button>
              </div>
            )}
          </div>
          <div className="hidden lg:flex justify-center">
            <img
              src="/images/GSC-logo-full.png"
              alt="Gov Services Connect"
              className="w-full max-w-xl h-auto"
            />
          </div>
        </div>
      </section>

      {/* How it works — the vendor journey */}
      <section className="max-w-5xl mx-auto px-4 pb-16">
        <h2 className="text-xl font-semibold tracking-tight text-center mb-8">
          How it works
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <StepCard
            number="1"
            icon={<Users size={24} />}
            title="Join the network"
            description="Tell us what you do. We verify your capabilities, NAICS codes, and past performance so you only see work you can actually win."
          />
          <StepCard
            number="2"
            icon={<FileSearch size={24} />}
            title="Get matched"
            description="We bring you the opportunities — federal, state, and local contracts that need your specialty, matched to what you qualify for."
          />
          <StepCard
            number="3"
            icon={<Handshake size={24} />}
            title="Deliver and grow"
            description="You do the work you're best at. We run the federal process end to end — compliance, proposals, invoicing — and you get paid."
          />
        </div>
      </section>

      {/* Value cards */}
      <section className="max-w-5xl mx-auto px-4 pb-16">
        <h2 className="text-xl font-semibold tracking-tight text-center mb-8">
          What we do
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <ValueCard
            icon={<Landmark size={24} />}
            title="Federal, State & Local"
            description="Opportunities at every level of government — set-asides, RFPs, RFQs, and task orders, refreshed continuously."
          />
          <ValueCard
            icon={<TrendingUp size={24} />}
            title="Consistent Work"
            description="A steady pipeline of engagements keeps your team billable year-round — not feast-or-famine."
          />
          <ValueCard
            icon={<FileText size={24} />}
            title="Paperwork Off Your Plate"
            description="Registration, compliance, proposals, and invoicing are on us. You focus on delivery."
          />
          <ValueCard
            icon={<Users size={24} />}
            title="Matched to What You Do"
            description="Opportunities are matched to your capabilities, set-asides, and NAICS codes — work you're qualified to win."
          />
        </div>
      </section>

      {/* Final CTA */}
      <section className="max-w-5xl mx-auto px-4 pb-16 text-center">
        <h2 className="text-lg font-semibold mb-4">
          Ready to grow with government work?
        </h2>
        <button
          onClick={() => router.push("/vendor-register")}
          className="bg-brand hover:bg-brand-hover text-white px-6 py-3 rounded-lg text-sm font-medium transition-colors"
        >
          Join Our Network
        </button>
      </section>

      {/* Footer */}
      <footer className="mt-auto border-t border-gsc-navy-line">
        <div className="max-w-5xl mx-auto px-4 py-6 text-center">
          <p className="text-xs text-gsc-dim">
            Gov Services Connect — We grow small businesses with consistent
            government work.
          </p>
        </div>
      </footer>
    </main>
  );
}

function StepCard({
  number,
  icon,
  title,
  description,
}: {
  number: string;
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="bg-gsc-navy-panel border border-gsc-navy-line rounded-xl p-8 text-center">
      <div className="text-brand mb-3 font-bold text-2xl">{number}</div>
      <div className="text-brand mb-3 flex justify-center">{icon}</div>
      <h3 className="text-lg font-semibold mb-3">{title}</h3>
      <p className="text-sm text-gsc-body leading-relaxed">{description}</p>
    </div>
  );
}

function ValueCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="bg-gsc-navy-panel border border-gsc-navy-line rounded-lg p-6 text-center">
      <div className="text-brand mb-3 flex justify-center">{icon}</div>
      <h3 className="text-sm font-semibold mb-2">{title}</h3>
      <p className="text-xs text-gsc-dim leading-relaxed">{description}</p>
    </div>
  );
}
