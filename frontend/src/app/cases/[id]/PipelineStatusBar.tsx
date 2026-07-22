"use client";

import { useState, useEffect, useCallback } from "react";
import { CheckCircle2, XCircle, Loader2, Circle } from "lucide-react";
import { getSolicitationByCase, type SolicitationWithDocuments } from "@/lib/api";

interface PipelineStatusBarProps {
  caseId: number;
}

type StepState = "pending" | "active" | "complete" | "failed" | "skipped";

interface Step {
  key: string;
  label: string;
  state: StepState;
  detail?: string | null;
}

const POLL_MS = 3000;

const STATE_TEXT_COLOR: Record<StepState, string> = {
  pending: "text-text-disabled",
  active: "text-warning",
  complete: "text-success",
  failed: "text-danger",
  skipped: "text-text-disabled",
};

const CONNECTOR_COLOR: Record<StepState, string> = {
  pending: "bg-border",
  active: "bg-border",
  complete: "bg-success",
  failed: "bg-border",
  skipped: "bg-border",
};

function StepIcon({ state }: { state: StepState }) {
  const cls = STATE_TEXT_COLOR[state];
  if (state === "active") return <Loader2 size={16} className={`${cls} animate-spin`} />;
  if (state === "complete" || state === "skipped") return <CheckCircle2 size={16} className={cls} />;
  if (state === "failed") return <XCircle size={16} className={cls} />;
  return <Circle size={16} className={cls} />;
}

function deriveSteps(sol: SolicitationWithDocuments): Step[] {
  const fetching: Step = {
    key: "fetching",
    label: "Fetching",
    state:
      sol.ingestion_status === "complete"
        ? "complete"
        : sol.ingestion_status === "failed"
          ? "failed"
          : sol.ingestion_status === "fetching"
            ? "active"
            : "pending",
    detail: sol.ingestion_status === "failed" ? sol.error_message : null,
  };

  const ingestionDone = sol.ingestion_status === "complete";
  const triaging: Step = {
    key: "triaging",
    label: "Triaging",
    state: !ingestionDone
      ? "pending"
      : sol.triage_status === "complete"
        ? "complete"
        : sol.triage_status === "failed"
          ? "failed"
          : sol.triage_status === "running"
            ? "active"
            : "pending",
    detail: sol.triage_status === "failed" ? sol.triage_error : null,
  };

  const triageDone = sol.triage_status === "complete";
  const quickKilled = sol.quick_kill === true;
  const matching: Step = {
    key: "matching",
    label: quickKilled && triageDone ? "Matching (skipped)" : "Matching",
    state: !triageDone
      ? "pending"
      : quickKilled
        ? "skipped"
        : sol.matching_status === "complete"
          ? "complete"
          : sol.matching_status === "failed"
            ? "failed"
            : sol.matching_status === "running"
              ? "active"
              : "pending",
    detail: sol.matching_status === "failed" ? sol.matching_error : quickKilled ? sol.quick_kill_reason : null,
  };

  const done: Step = {
    key: "done",
    label: "Done",
    state: matching.state === "complete" || matching.state === "skipped" ? "complete" : "pending",
  };

  return [fetching, triaging, matching, done];
}

export default function PipelineStatusBar({ caseId }: PipelineStatusBarProps) {
  const [sol, setSol] = useState<SolicitationWithDocuments | null>(null);

  const refresh = useCallback(async () => {
    try {
      const s = await getSolicitationByCase(caseId);
      setSol(s);
    } catch {
      setSol(null);
    }
  }, [caseId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const isActive =
    sol?.ingestion_status === "fetching" ||
    sol?.triage_status === "running" ||
    sol?.matching_status === "running";

  useEffect(() => {
    if (!isActive) return;
    const id = setInterval(refresh, POLL_MS);
    return () => clearInterval(id);
  }, [isActive, refresh]);

  if (!sol) return null;

  const steps = deriveSteps(sol);

  return (
    <div className="shrink-0 bg-surface-1 border-b border-border px-4 py-2.5">
      <div className="flex items-center max-w-5xl mx-auto">
        {steps.map((step, i) => (
          <div key={step.key} className="flex items-center flex-1 last:flex-none">
            <div
              className="flex items-center gap-1.5 shrink-0"
              title={step.detail || undefined}
            >
              <StepIcon state={step.state} />
              <span className={`text-xs font-medium whitespace-nowrap ${STATE_TEXT_COLOR[step.state]}`}>
                {step.label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div className={`h-px flex-1 mx-2 ${CONNECTOR_COLOR[step.state]}`} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
