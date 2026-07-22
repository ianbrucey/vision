"use client";

import ReferenceNav from "@/components/ReferenceNav";
import ForecastsTab from "@/app/cases/[id]/tabs/ForecastsTab";

export default function ForecastsPage() {
  return (
    <div className="h-dvh bg-surface-0 text-text-primary flex flex-col">
      <ReferenceNav />
      <div className="flex-1 flex flex-col min-h-0">
        <ForecastsTab caseId={null} />
      </div>
    </div>
  );
}
