import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import AuthProvider from "@/components/AuthProvider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Gov Services Connect",
  description:
    "We grow small businesses with consistent government work. Join our vendor network for federal, state, and local government contracts.",
  openGraph: {
    title: "Gov Services Connect",
    description:
      "We grow small businesses with consistent government work — federal, state, and local government contracts.",
    type: "website",
  },
};

const organizationJsonLd = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "Gov Services Connect",
  slogan: "We grow small businesses with consistent government work.",
  description:
    "Government services staffing and sourcing firm that matches small-business vendors to federal, state, and local government contracts. We handle registration, compliance, proposals, and invoicing; vendors deliver the work.",
  areaServed: "United States",
  knowsAbout: [
    "government contracting",
    "government staffing",
    "government sourcing",
    "federal contracting",
    "small business set-asides",
    "RFPs",
    "RFQs",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <AuthProvider>{children}</AuthProvider>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationJsonLd) }}
        />
      </body>
    </html>
  );
}
