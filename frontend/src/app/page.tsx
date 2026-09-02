"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { useEffect, useRef, useCallback } from "react";
import {
  FileSearch,
  Users,
  FileText,
  TrendingUp,
  Landmark,
  Handshake,
  ShieldCheck,
  MapPin,
  HardHat,
  ArrowRight,
  ChevronRight,
  Mail,
  Phone,
  Building2,
  ExternalLink,
  Award,
} from "lucide-react";

/* ────────────────────────────────────────────
   Scroll Animation Hook (IntersectionObserver)
   ──────────────────────────────────────────── */

function useScrollAnimation() {
  const observerRef = useRef<IntersectionObserver | null>(null);

  const observe = useCallback((node: HTMLElement | null) => {
    if (!node) return;
    if (!observerRef.current) {
      observerRef.current = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.remove("scroll-hidden");
              entry.target.classList.add("scroll-animate");
              observerRef.current?.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
      );
    }
    node.classList.add("scroll-hidden");
    observerRef.current.observe(node);
  }, []);

  useEffect(() => {
    return () => observerRef.current?.disconnect();
  }, []);

  return observe;
}

/* ────────────────────────────────────────────
   Counter Animation Hook
   ──────────────────────────────────────────── */

function useCountUp(target: number, duration = 1800) {
  const ref = useRef<HTMLSpanElement>(null);
  const hasAnimated = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated.current) {
          hasAnimated.current = true;
          const start = performance.now();
          const step = (now: number) => {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
            el.textContent = Math.round(eased * target).toLocaleString();
            if (progress < 1) requestAnimationFrame(step);
          };
          requestAnimationFrame(step);
          observer.unobserve(el);
        }
      },
      { threshold: 0.5 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [target, duration]);

  return ref;
}

/* ────────────────────────────────────────────
   Landing Page
   ──────────────────────────────────────────── */

export default function LandingPage() {
  const { user } = useAuth();
  const router = useRouter();
  const animate = useScrollAnimation();

  return (
    <main className="min-h-dvh text-white flex flex-col">
      {/* ── Top Announcement / SAM.gov Bar ── */}
      <div className="bg-gsc-navy-panel/90 border-b border-gsc-navy-line text-xs py-1.5 px-4 text-center text-gsc-body flex items-center justify-center gap-4 flex-wrap">
        <span className="inline-flex items-center gap-1.5 text-white font-medium">
          <ShieldCheck size={14} className="text-brand" /> SAM.gov Registered Prime Contractor
        </span>
        <span className="hidden sm:inline text-gsc-navy-line">•</span>
        <span>CAGE: <strong className="text-white">21GM9</strong></span>
        <span className="hidden sm:inline text-gsc-navy-line">•</span>
        <span>UEI: <strong className="text-white">MU8FAL4JBL91</strong></span>
        <span className="hidden md:inline text-gsc-navy-line">•</span>
        <span className="hidden md:inline">Justice Quest LLC Sourcing Division</span>
      </div>

      {/* ── Header ── */}
      <header className="sticky top-0 z-30 bg-gsc-navy/90 backdrop-blur-md border-b border-white/10">
        <div className="max-w-6xl mx-auto flex items-center justify-between h-16 px-4 lg:px-6">
          <img
            src="/images/GSC-logo-short.png"
            alt="Gov Services Connect"
            className="h-10 w-auto"
          />
          <div className="flex items-center gap-3">
            <a
              href="tel:4707853007"
              className="hidden md:inline-flex items-center gap-1.5 text-xs text-gsc-body hover:text-white px-3 py-2 rounded-lg transition-colors"
            >
              <Phone size={14} className="text-brand" /> (470) 785-3007
            </a>
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
                  onClick={() => router.push("/login")}
                  className="text-gsc-body hover:text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors"
                >
                  Sign In
                </button>
                <button
                  onClick={() => router.push("/vendor-register")}
                  className="bg-brand hover:bg-brand-hover text-white px-5 py-2 rounded-lg text-sm font-semibold transition-colors btn-lift"
                >
                  Join Our Network
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="hero-gradient-bg relative overflow-hidden">
        {/* Subtle radial overlay for depth */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(184,134,11,0.08)_0%,transparent_60%)]" />

        <div className="max-w-6xl mx-auto px-4 lg:px-6 flex items-center min-h-[calc(100dvh-6rem)] relative z-10">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-16 items-center w-full py-12 lg:py-0">
            {/* Copy */}
            <div className="text-center lg:text-left">
              {/* Trust badge */}
              <div className="inline-flex items-center gap-2 bg-white/8 border border-white/12 rounded-full px-4 py-1.5 mb-6">
                <Award size={14} className="text-brand" />
                <span className="text-xs font-medium text-gsc-body">
                  Prime Contractor Sourcing Network — Justice Quest LLC
                </span>
              </div>

              <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight mb-6 leading-tight">
                We grow small businesses with{" "}
                <span className="text-brand">consistent government work.</span>
              </h1>

              <p className="text-gsc-body max-w-xl mx-auto lg:mx-0 mb-8 leading-relaxed text-base lg:text-lg">
                Federal, state, and local agencies need specialized trades — construction,
                IT, facilities, and services. We source those contracts, match them to
                your capabilities, and handle every piece of federal compliance and paperwork so
                you can focus on delivery.
              </p>

              {user ? (
                <button
                  onClick={() => router.push("/solicitations")}
                  className="bg-brand hover:bg-brand-hover text-white px-8 py-3.5 rounded-lg text-sm font-semibold transition-colors btn-lift"
                >
                  Go to Dashboard
                </button>
              ) : (
                <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-3">
                  <button
                    onClick={() => router.push("/vendor-register")}
                    className="w-full sm:w-auto bg-brand hover:bg-brand-hover text-white px-8 py-3.5 rounded-lg text-sm font-semibold transition-colors btn-lift inline-flex items-center justify-center gap-2"
                  >
                    Join Our Network
                    <ArrowRight size={16} />
                  </button>
                  <button
                    onClick={() => {
                      document
                        .getElementById("how-it-works")
                        ?.scrollIntoView({ behavior: "smooth" });
                    }}
                    className="w-full sm:w-auto border border-white/20 text-white hover:bg-white/8 px-8 py-3.5 rounded-lg text-sm font-medium transition-colors"
                  >
                    Learn How It Works
                  </button>
                </div>
              )}
            </div>

            {/* Logo */}
            <div className="hidden lg:flex justify-center">
              <img
                src="/images/GSC-logo-full.png"
                alt="Gov Services Connect"
                className="w-full max-w-md h-auto drop-shadow-2xl"
              />
            </div>
          </div>
        </div>
      </section>

      {/* ── Trust Bar — Key Stats & Identifiers ── */}
      <section className="bg-gsc-navy-panel border-y border-gsc-navy-line">
        <div
          className="max-w-6xl mx-auto px-4 lg:px-6 py-8 lg:py-10"
          ref={animate}
        >
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 lg:gap-8">
            <StatCounter
              value={250}
              suffix="+"
              label="Active Federal Opportunities"
              icon={<FileSearch size={20} />}
            />
            <StatCounter
              value={50}
              suffix=" States"
              label="Nationwide Coverage"
              icon={<MapPin size={20} />}
            />
            <StatCounter
              value={12}
              suffix="+"
              label="Trade Specialties"
              icon={<HardHat size={20} />}
            />
            <StatCounter
              value={100}
              prefix="$"
              suffix="K+"
              label="Avg. Contract Value"
              icon={<TrendingUp size={20} />}
            />
          </div>
        </div>
      </section>

      {/* ── How It Works ── */}
      <section
        id="how-it-works"
        className="bg-gsc-navy py-16 lg:py-24"
      >
        <div className="max-w-6xl mx-auto px-4 lg:px-6">
          <div className="text-center mb-12" ref={animate}>
            <h2 className="text-2xl lg:text-3xl font-bold tracking-tight mb-3">
              How it works
            </h2>
            <p className="text-gsc-body max-w-2xl mx-auto">
              Three steps to consistent government work — no red tape on your end.
            </p>
          </div>

          <div
            className="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-4"
            ref={animate}
          >
            <StepCard
              number="1"
              icon={<Users size={28} />}
              title="Join the network"
              description="Tell us your trade, location, and capabilities. We verify your credentials once — licenses, insurance, NAICS codes — so you only see work you can win."
              delay="stagger-1"
            />
            <StepCard
              number="2"
              icon={<FileSearch size={28} />}
              title="Get matched"
              description="Our system scans federal, state, and local portals daily. When a contract fits your specialty, you get notified with a clear summary — no jargon, no guesswork."
              delay="stagger-2"
            />
            <StepCard
              number="3"
              icon={<Handshake size={28} />}
              title="Deliver & get paid"
              description="You do the work you're best at. We handle compliance, proposals, and invoicing end to end as the prime contractor. You deliver, we manage the process, everyone gets paid."
              delay="stagger-3"
            />
          </div>
        </div>
      </section>

      {/* ── Why Vendors Choose Us ── */}
      <section className="bg-gsc-navy-panel py-16 lg:py-24">
        <div className="max-w-6xl mx-auto px-4 lg:px-6">
          <div className="text-center mb-12" ref={animate}>
            <h2 className="text-2xl lg:text-3xl font-bold tracking-tight mb-3">
              Why vendors choose us
            </h2>
            <p className="text-gsc-body max-w-2xl mx-auto">
              We exist to make government contracting accessible to small businesses
              that can do the work but can&apos;t navigate the federal bureaucracy.
            </p>
          </div>

          <div className="space-y-6 lg:space-y-8">
            <FeatureRow
              icon={<Landmark size={24} />}
              title="Opportunities at every level"
              description="Federal set-asides, state RFPs, local task orders — we scan them all. Construction, IT, facilities, professional services. Refreshed daily so you never miss a deadline."
              animateRef={animate}
              reverse={false}
            />
            <FeatureRow
              icon={<TrendingUp size={24} />}
              title="Steady pipeline, not feast-or-famine"
              description="Government work is recurring. Agencies re-procure, task orders renew, IDIQs run for years. We keep your pipeline full so your crew stays billable year-round."
              animateRef={animate}
              reverse={true}
            />
            <FeatureRow
              icon={<FileText size={24} />}
              title="We handle the federal process"
              description="SAM.gov registration, bonding guidance, proposal writing, compliance checklists, progress invoicing — the back-office burden that stops most small businesses from bidding. That's on us."
              animateRef={animate}
              reverse={false}
            />
            <FeatureRow
              icon={<Users size={24} />}
              title="Smart matching by trade, location & capacity"
              description="Every opportunity is matched against your NAICS codes, geographic reach, and current availability. You only see contracts you're qualified to win and capable of delivering."
              animateRef={animate}
              reverse={true}
            />
          </div>
        </div>
      </section>

      {/* ── Social Proof / Stats ── */}
      <section className="bg-gsc-navy py-16 lg:py-24">
        <div className="max-w-6xl mx-auto px-4 lg:px-6">
          <div className="text-center mb-12" ref={animate}>
            <h2 className="text-2xl lg:text-3xl font-bold tracking-tight mb-3">
              The opportunity is real
            </h2>
            <p className="text-gsc-body max-w-2xl mx-auto">
              The federal government spends hundreds of billions a year and is
              required by law to award a share to small businesses. Most small
              contractors never bid — not because they can&apos;t do the work,
              but because the process defeats them.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6" ref={animate}>
            <ProofCard
              stat="~250"
              label="active federal construction opportunities set aside for small business — this week alone"
            />
            <ProofCard
              stat="$100K–$150K+"
              label="typical contract range — big enough to build a real business, small enough that the giants don't compete"
            />
            <ProofCard
              stat="23%"
              label="federal contracting dollars mandated for small business — it's the law, and agencies must hit their targets"
            />
          </div>
        </div>
      </section>

      {/* ── Final CTA ── */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-gsc-navy-panel via-gsc-navy to-gsc-navy-panel" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(184,134,11,0.06)_0%,transparent_70%)]" />

        <div
          className="max-w-3xl mx-auto px-4 lg:px-6 py-20 lg:py-28 text-center relative z-10"
          ref={animate}
        >
          <h2 className="text-2xl lg:text-4xl font-bold tracking-tight mb-4">
            Your next government contract is waiting.
          </h2>
          <p className="text-gsc-body text-base lg:text-lg mb-8 max-w-xl mx-auto">
            Join our vendor network and start receiving matched opportunities.
            You do the work — we handle the process.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={() => router.push("/vendor-register")}
              className="w-full sm:w-auto bg-brand hover:bg-brand-hover text-white px-10 py-4 rounded-lg text-base font-semibold transition-colors btn-lift inline-flex items-center justify-center gap-2"
            >
              Join Our Network
              <ChevronRight size={18} />
            </button>
            <a
              href="tel:4707853007"
              className="w-full sm:w-auto border border-white/20 hover:bg-white/8 text-white px-8 py-4 rounded-lg text-base font-medium transition-colors inline-flex items-center justify-center gap-2"
            >
              <Phone size={18} className="text-brand" /> Call (470) 785-3007
            </a>
          </div>
          <p className="text-gsc-dim text-xs mt-4">
            No cost to register. No obligation.
          </p>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="bg-gsc-navy-panel border-t border-gsc-navy-line">
        <div className="max-w-6xl mx-auto px-4 lg:px-6 py-10 lg:py-12">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
            {/* Brand */}
            <div className="sm:col-span-2 lg:col-span-1">
              <img
                src="/images/GSC-logo-short.png"
                alt="Gov Services Connect"
                className="h-8 w-auto mb-3"
              />
              <p className="text-xs text-gsc-dim leading-relaxed max-w-xs mb-3">
                Gov Services Connect is a specialized vendor sourcing division of{" "}
                <strong className="text-gsc-body">Justice Quest LLC</strong>.
              </p>
              <a
                href="https://JusticeQuest.pro"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs text-brand hover:underline"
              >
                <Building2 size={13} /> Visit JusticeQuest.pro <ExternalLink size={11} />
              </a>
            </div>

            {/* For Vendors */}
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">
                For Vendors
              </h4>
              <ul className="space-y-2">
                <FooterLink
                  label="Join Our Network"
                  onClick={() => router.push("/vendor-register")}
                />
                <FooterLink
                  label="Sign In"
                  onClick={() => router.push("/login")}
                />
                <FooterLink
                  label="How It Works"
                  onClick={() =>
                    document
                      .getElementById("how-it-works")
                      ?.scrollIntoView({ behavior: "smooth" })
                  }
                />
              </ul>
            </div>

            {/* Company & Compliance */}
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">
                Federal Registration
              </h4>
              <ul className="space-y-1.5 text-xs text-gsc-dim">
                <li><strong className="text-gsc-body">CAGE:</strong> 21GM9</li>
                <li><strong className="text-gsc-body">UEI:</strong> MU8FAL4JBL91</li>
                <li><strong className="text-gsc-body">NAICS:</strong> 541511, 236220</li>
                <li><strong className="text-gsc-body">Entity:</strong> Justice Quest LLC</li>
              </ul>
            </div>

            {/* Contact */}
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">
                Contact Us
              </h4>
              <ul className="space-y-2">
                <li className="flex items-center gap-2 text-xs text-gsc-dim">
                  <Mail size={14} className="text-brand shrink-0" />
                  <a href="mailto:admin@govservicesconnect.com" className="hover:text-white transition-colors">
                    admin@govservicesconnect.com
                  </a>
                </li>
                <li className="flex items-center gap-2 text-xs text-gsc-dim">
                  <Phone size={14} className="text-brand shrink-0" />
                  <a href="tel:4707853007" className="hover:text-white transition-colors">
                    (470) 785-3007
                  </a>
                </li>
              </ul>
            </div>
          </div>

          {/* Bottom bar */}
          <div className="mt-8 pt-6 border-t border-gsc-navy-line flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-gsc-dim">
            <p>
              © {new Date().getFullYear()} Justice Quest LLC (dba Gov Services Connect). All rights reserved.
            </p>
            <p>
              Build. Source. Deliver. — Connecting Government & Industry
            </p>
          </div>
        </div>
      </footer>
    </main>
  );
}

/* ────────────────────────────────────────────
   Sub-Components
   ──────────────────────────────────────────── */

function StatCounter({
  value,
  prefix = "",
  suffix = "",
  label,
  icon,
}: {
  value: number;
  prefix?: string;
  suffix?: string;
  label: string;
  icon: React.ReactNode;
}) {
  const countRef = useCountUp(value);

  return (
    <div className="text-center">
      <div className="text-brand mb-2 flex justify-center">{icon}</div>
      <div className="text-2xl lg:text-3xl font-bold text-white stat-shimmer">
        {prefix}
        <span ref={countRef}>0</span>
        {suffix}
      </div>
      <p className="text-xs text-gsc-dim mt-1">{label}</p>
    </div>
  );
}

function StepCard({
  number,
  icon,
  title,
  description,
  delay,
}: {
  number: string;
  icon: React.ReactNode;
  title: string;
  description: string;
  delay: string;
}) {
  return (
    <div
      className={`step-connector ${delay} bg-gsc-navy-panel border border-gsc-navy-line rounded-xl p-6 lg:p-8 text-center hover:border-brand/30 transition-colors duration-150`}
    >
      {/* Step number circle */}
      <div className="w-10 h-10 rounded-full bg-brand/15 border border-brand/30 flex items-center justify-center mx-auto mb-4">
        <span className="text-brand font-bold text-sm">{number}</span>
      </div>
      <div className="text-brand mb-4 flex justify-center">{icon}</div>
      <h3 className="text-lg font-semibold mb-3">{title}</h3>
      <p className="text-sm text-gsc-body leading-relaxed">{description}</p>
    </div>
  );
}

function FeatureRow({
  icon,
  title,
  description,
  animateRef,
  reverse,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  animateRef: (node: HTMLElement | null) => void;
  reverse: boolean;
}) {
  return (
    <div
      ref={animateRef}
      className={`flex flex-col ${
        reverse ? "md:flex-row-reverse" : "md:flex-row"
      } items-center gap-6 lg:gap-10 bg-gsc-navy/50 border border-gsc-navy-line rounded-xl p-6 lg:p-8 hover:border-brand/20 transition-colors duration-150`}
    >
      {/* Icon block */}
      <div className="shrink-0 w-16 h-16 rounded-xl bg-brand/10 border border-brand/20 flex items-center justify-center">
        <div className="text-brand">{icon}</div>
      </div>
      {/* Text */}
      <div className={`text-center ${reverse ? "md:text-right" : "md:text-left"}`}>
        <h3 className="text-lg font-semibold mb-2">{title}</h3>
        <p className="text-sm text-gsc-body leading-relaxed">{description}</p>
      </div>
    </div>
  );
}

function ProofCard({ stat, label }: { stat: string; label: string }) {
  return (
    <div className="bg-gsc-navy-panel border border-gsc-navy-line rounded-xl p-6 lg:p-8 text-center hover:border-brand/30 transition-colors duration-150">
      <div className="text-2xl lg:text-3xl font-bold text-brand mb-3">
        {stat}
      </div>
      <p className="text-sm text-gsc-body leading-relaxed">{label}</p>
    </div>
  );
}

function FooterLink({
  label,
  onClick,
}: {
  label: string;
  onClick: () => void;
}) {
  return (
    <li>
      <button
        onClick={onClick}
        className="text-sm text-gsc-dim hover:text-brand transition-colors duration-150"
      >
        {label}
      </button>
    </li>
  );
}
