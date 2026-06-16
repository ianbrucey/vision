"use client";

import { useCallback } from "react";
import { Printer } from "lucide-react";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface HtmlRendererProps {
  /** The HTML string to render (full document with <style>, <body>, etc.) */
  html: string;
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

/**
 * Renders agent-generated HTML in a sandboxed iframe with a print button.
 *
 * Security: the iframe uses sandbox="" (no permissions) so no JavaScript
 * in the HTML will execute. Safe for agent-generated content.
 *
 * Print: creates a Blob URL from the HTML, opens it in a new window,
 * triggers print, then closes the window. This bypasses iframe sandbox
 * restrictions on contentWindow access.
 */
export default function HtmlRenderer({ html }: HtmlRendererProps) {
  const handlePrint = useCallback(() => {
    // Create a blob from the HTML string and open in a new window.
    // This gives full DOM access for printing without sandbox restrictions.
    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const printWindow = window.open(url, "_blank");

    if (!printWindow) {
      // Popup blocked — alert the user
      alert("Print popup was blocked. Please allow popups for this site.");
      return;
    }

    // Wait for the window to load, then print
    printWindow.onload = () => {
      printWindow.focus();
      printWindow.print();
      // Clean up the blob URL after print dialog closes
      printWindow.addEventListener("afterprint", () => {
        printWindow.close();
        URL.revokeObjectURL(url);
      }, { once: true });
      // Fallback: if afterprint doesn't fire (e.g. user cancels immediately),
      // still clean up on window close
      const cleanupInterval = setInterval(() => {
        if (printWindow.closed) {
          URL.revokeObjectURL(url);
          clearInterval(cleanupInterval);
        }
      }, 500);
    };
  }, [html]);

  if (!html) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <p className="text-sm text-[--text-disabled]">No HTML content</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Toolbar */}
      <div className="shrink-0 flex items-center justify-between px-4 py-2 bg-[--surface-1] border-b border-[--border]">
        <span className="text-xs text-[--text-secondary]">
          Agent-generated HTML &bull; Read-only
        </span>
        <button
          onClick={handlePrint}
          className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded border border-[--border] bg-[--surface-1] hover:bg-[--surface-3] text-[--text-primary] transition-colors"
        >
          <Printer size={14} />
          <span className="hidden sm:inline">Print</span>
        </button>
      </div>

      {/* Document preview — white page on grey surface */}
      <div className="flex-1 overflow-auto bg-[--surface-0] p-4 md:p-8">
        <iframe
          srcDoc={html}
          sandbox=""
          title="HTML Preview"
          className="block mx-auto border-0 bg-white shadow-lg"
          style={{
            width: "8.5in",
            minHeight: "11in",
            maxWidth: "100%",
          }}
        />
      </div>
    </div>
  );
}
