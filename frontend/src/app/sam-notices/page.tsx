"use client";

import ReferenceNav from "@/components/ReferenceNav";
import SamNoticesTab from "@/app/cases/[id]/tabs/SamNoticesTab";

export default function SamNoticesPage() {
  return (
    <div className="h-dvh bg-surface-0 text-text-primary flex flex-col">
      <ReferenceNav />
      <div className="flex-1 flex flex-col min-h-0">
        <SamNoticesTab caseId={null} />
      </div>
    </div>
  );
}
