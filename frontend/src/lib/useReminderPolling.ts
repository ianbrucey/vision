"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { listReminders, updateReminder, type Reminder } from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface ReminderPollingOptions {
  /** Polling interval in milliseconds (default 30_000) */
  intervalMs?: number;
  /** Callback when a reminder fires (for custom UI handling) */
  onFire?: (reminder: Reminder) => void;
  /** Callback when a reminder is dismissed */
  onDismiss?: (reminderId: number) => void;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function requestNotificationPermission(): "granted" | "denied" | "default" {
  if (typeof window === "undefined" || !("Notification" in window)) {
    return "denied";
  }
  return Notification.permission as "granted" | "denied" | "default";
}

async function sendBrowserNotification(reminder: Reminder): Promise<void> {
  if (typeof window === "undefined" || !("Notification" in window)) return;

  const permission = Notification.permission;
  if (permission !== "granted") return;

  const categoryLabel =
    reminder.category.charAt(0).toUpperCase() + reminder.category.slice(1);

  try {
    new Notification("Reminder — Vision", {
      body: `${reminder.title}\n${categoryLabel} · Due now`,
      icon: "/favicon.ico",
      tag: `reminder-${reminder.id}`, // prevents duplicate notifications
      requireInteraction: false,
    });
  } catch {
    // Browser may throttle or reject — silently ignore
  }
}

function showInAppToast(reminder: Reminder): void {
  // Dispatch a custom event that the toast system listens to.
  // This avoids coupling to a specific toast implementation.
  if (typeof window !== "undefined") {
    window.dispatchEvent(
      new CustomEvent("vision:reminder-fired", {
        detail: {
          id: reminder.id,
          type: "warning",
          title: `Reminder: ${reminder.title}`,
          description: `${reminder.category} · Due now`,
        },
      }),
    );
  }
}

/* ------------------------------------------------------------------ */
/* Hook                                                                */
/* ------------------------------------------------------------------ */

export function useReminderPolling(
  caseId: number,
  options: ReminderPollingOptions = {},
) {
  const { intervalMs = 30_000, onFire, onDismiss } = options;

  const firedIdsRef = useRef<Set<number>>(new Set());
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const visibilityRef = useRef<boolean>(true);

  /* ---- Visibility API — pause polling when tab is hidden ---- */
  useEffect(() => {
    const handleVisibility = () => {
      visibilityRef.current = document.visibilityState === "visible";
    };
    document.addEventListener("visibilitychange", handleVisibility);
    return () =>
      document.removeEventListener("visibilitychange", handleVisibility);
  }, []);

  /* ---- Check for due reminders ---- */
  const checkReminders = useCallback(async () => {
    if (!visibilityRef.current) return; // don't poll when hidden

    try {
      const res = await listReminders(caseId, { status: "pending" });
      const now = new Date();

      for (const reminder of res.reminders) {
        const remindAt = new Date(reminder.remind_at);

        if (remindAt <= now && !firedIdsRef.current.has(reminder.id)) {
          // Mark as fired to prevent re-fire within this session
          firedIdsRef.current.add(reminder.id);

          // Show notifications
          showInAppToast(reminder);
          sendBrowserNotification(reminder);
          onFire?.(reminder);

          // Update status in the database
          try {
            await updateReminder(reminder.id, { status: "fired" });
          } catch {
            // If the update fails, the reminder will be re-checked next poll.
            // Remove from fired set so it retries.
            firedIdsRef.current.delete(reminder.id);
          }
        }
      }
    } catch {
      // Network errors are silent — the next poll will retry
    }
  }, [caseId, onFire]);

  /* ---- Start polling ---- */
  useEffect(() => {
    // Initial check
    checkReminders();

    // Periodic polling
    pollingRef.current = setInterval(checkReminders, intervalMs);

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [checkReminders, intervalMs]);

  /* ---- Notification permission banner (one-time) ---- */
  useEffect(() => {
    if (typeof window === "undefined" || !("Notification" in window)) return;

    const stored = localStorage.getItem("vision_notify_permission");
    if (stored) return; // user already decided

    if (Notification.permission === "default") {
      // Defer by 2 seconds so the page loads first
      const timer = setTimeout(async () => {
        try {
          const result = await Notification.requestPermission();
          localStorage.setItem("vision_notify_permission", result);
        } catch {
          localStorage.setItem("vision_notify_permission", "denied");
        }
      }, 2000);

      return () => clearTimeout(timer);
    }
  }, []);

  /* ---- Return controls ---- */
  return {
    /** Manually check for due reminders (in addition to polling) */
    checkNow: checkReminders,
  };
}

/* ------------------------------------------------------------------ */
/* Companion hook: dismiss a single reminder                           */
/* ------------------------------------------------------------------ */

export function useDismissReminder() {
  return useCallback(
    async (reminderId: number): Promise<boolean> => {
      try {
        await updateReminder(reminderId, { status: "dismissed" });
        return true;
      } catch {
        return false;
      }
    },
    [],
  );
}

/* ------------------------------------------------------------------ */
/* Permission banner state (for UI components)                         */
/* ------------------------------------------------------------------ */

export function useNotificationPermission(): {
  permission: "granted" | "denied" | "default";
  requestPermission: () => Promise<"granted" | "denied">;
} {
  const [permission, setPermission] = useState<
    "granted" | "denied" | "default"
  >(() => requestNotificationPermission());

  const requestPermission = useCallback(async () => {
    if (typeof window === "undefined" || !("Notification" in window)) {
      return "denied" as const;
    }
    try {
      const result = await Notification.requestPermission();
      const perm = result as "granted" | "denied";
      localStorage.setItem("vision_notify_permission", perm);
      setPermission(perm);
      return perm;
    } catch {
      localStorage.setItem("vision_notify_permission", "denied");
      setPermission("denied");
      return "denied" as const;
    }
  }, []);

  return { permission, requestPermission };
}
