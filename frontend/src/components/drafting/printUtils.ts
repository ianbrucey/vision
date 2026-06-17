/**
 * Print a legal draft with formatting identical to the screen rendering.
 * Captures the innerHTML of the .draft-preview-shell element and wraps it
 * in a complete HTML document with the same CSS used for screen rendering.
 */

const PRINT_CSS = `
body {
  font-family: "Times New Roman", Times, Georgia, serif;
  font-size: 14pt;
  line-height: 2.0;
  margin: 0;
  padding: 0;
  color: black;
  background: white;
}
.draft-document {
  font-family: "Times New Roman", Times, Georgia, serif;
  font-size: 14pt;
  line-height: 2.0;
  background: white;
  color: black;
  overflow-wrap: break-word;
}
.draft-document.draft-letter { font-size: 12pt; line-height: 1.7; }
.court-caption { text-align: center; font-weight: bold; margin-bottom: 2em; }
.case-caption { width: 100%; margin-bottom: 2em; border-collapse: collapse; }
.case-caption td { vertical-align: top; padding: 0.5em; }
.case-left { width: 50%; }
.case-right { width: 50%; text-align: center; border-left: 1px solid black; padding-left: 1em; }
.motion-title { text-align: center; font-weight: bold; margin: 2em 0; text-decoration: underline; }
.section-header { font-weight: bold; margin: 1.5em 0 1em 0; text-align: center; text-decoration: underline; text-transform: uppercase; }
.argument-subheading { font-weight: bold; margin: 1.25em 0 0.75em 0; }
.draft-document p { margin: 1em 0; text-align: justify; }
.para-num { font-weight: bold; margin-right: 0.25em; }
.draft-list-item { display: block; margin-left: 2em; text-indent: -1.5em; padding-left: 1.5em; }
.list-label { display: inline-block; min-width: 2em; margin-right: 0.5em; }
.draft-document blockquote { margin: 1em 2em; padding: 0.5em 1em; border-left: 3px solid #ccc; font-style: italic; }
.signature-row { margin-top: 3em; margin-bottom: 1em; max-width: 300px; }
.signature-line { border-top: 1px solid black; margin-bottom: 4px; }
.signature-name { font-weight: bold; }
.section-divider { margin: 2em 0; border: 0; border-top: 1px solid #eee; }
.letter-date { margin-bottom: 2em; }
.letter-recipient { margin: 2em 0; }
.letter-salutation { margin-bottom: 1.5em; }
.letter-subject { font-weight: bold; margin-bottom: 1.5em; }
.letter-signoff { margin-top: 2em; margin-bottom: 2em; }
.document-title { margin-bottom: 2em; text-align: center; font-weight: bold; font-size: 1.2em; text-transform: uppercase; }
.contract-parties { display: grid; grid-template-columns: 1fr 1fr; gap: 2em; margin-bottom: 2em; }
.contract-party-label { font-size: 0.8em; color: #666; margin-top: 0.25em; }
.memo-header-table { width: 100%; margin-bottom: 2em; border-bottom: 2px solid #ddd; padding-bottom: 1em; }
.memo-header-table td { padding: 0.25em 0; vertical-align: top; }
.memo-header-label { font-weight: bold; padding-right: 1em; white-space: nowrap; }
.raw-html-block { margin: 1em 0; }
.raw-html-block table { width: 100%; border-collapse: collapse; margin: 0.5em 0; }
.raw-html-block th, .raw-html-block td { border: 1px solid #ccc; padding: 0.4em 0.75em; text-align: left; }
.raw-html-block th { background: #f0f0f0; font-weight: bold; }
.editable-block, .editable-caption-field { cursor: default; }
.editable-block:hover, .editable-caption-field:hover { background: none; outline: none; }
.edit-textarea, .edit-actions, .btn-save, .btn-cancel, .insert-row, .insert-row-btn, .insert-row-line { display: none; }

@page { size: letter; margin: 1in; }
@media print {
  body { background: white; }
  .draft-preview-shell { max-width: none; margin: 0; padding: 0; box-shadow: none; border: none; }
}
`;

export function printDraft(innerHtml: string): void {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <style>${PRINT_CSS}</style>
</head>
<body>
  <div class="draft-preview-shell">${innerHtml}</div>
</body>
</html>`;

  const blob = new Blob([html], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  const win = window.open(url, "_blank");
  if (!win) {
    alert("Print popup was blocked. Please allow popups for this site.");
    return;
  }
  win.onload = () => {
    win.focus();
    win.print();
    win.addEventListener("afterprint", () => {
      win.close();
      URL.revokeObjectURL(url);
    }, { once: true });
  };
}
