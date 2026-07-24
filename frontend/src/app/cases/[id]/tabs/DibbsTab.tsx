"use client";

interface Props { caseId: number; }

export default function DibbsTab({ caseId: _caseId }: Props) {
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="text-center">
        <p className="text-sm font-medium text-text-primary">DIBBS RFQs</p>
        <p className="text-xs text-text-disabled mt-1">Coming soon.</p>
      </div>
    </div>
  );
}
