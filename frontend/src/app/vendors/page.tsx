"use client";

import ReferenceNav from "@/components/ReferenceNav";
import VendorsTab from "@/app/cases/[id]/tabs/VendorsTab";

export default function VendorsPage() {
  return (
    <div className="h-dvh bg-surface-0 text-text-primary flex flex-col">
      <ReferenceNav />
      <div className="flex-1 flex flex-col min-h-0">
        <VendorsTab caseId={0} />
      </div>
    </div>
  );
}
