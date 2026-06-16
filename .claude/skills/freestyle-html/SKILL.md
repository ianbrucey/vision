---
name: freestyle-html
description: Produce print-formatted 8.5×11 legal letters and documents as self-contained HTML. Use when asked to draft an engagement letter, dispute letter, demand letter, notice, or any formal correspondence that should be printable.
---

# Freestyle HTML — Printable Legal Documents

When the user asks you to draft a formal letter or legal document that needs to be printed, produce an `html` workspace item in the `freestyle` folder. The HTML is rendered in a sandboxed iframe with a Print button — the user can print it directly from the workspace.

---

## When to Use This Skill

**Trigger phrases:**
- "Draft an engagement letter"
- "Write a dispute letter to Equifax"
- "Create a demand letter for..."
- "Generate a formal notice"
- Any request for a printable, formally formatted legal document

**Do NOT use for:**
- Structured data views → use `json_view` (table, list, cards, chart)
- Markdown notes or analysis → use `markdown`
- Block-structured drafts → use `structured_draft`

---

## How to Create an HTML Letter

Use `create_workspace_item`:

```
create_workspace_item(
  name="Engagement Letter — Smith",
  file_type="html",
  folder="freestyle",
  content=[{"html": "<!DOCTYPE html>...full document..."}]
)
```

**Content format:** The `content` field must be an array with a single object containing an `html` key:
```json
[{"html": "<!DOCTYPE html><html>...</html>"}]
```

---

## Required CSS Template

Every HTML letter MUST include this base CSS in a `<style>` tag in the `<head>`. You may customize the letterhead colors, fonts, and body content — but the print dimensions and structure must follow this template:

```css
@page {
  size: letter;
  margin: 1in;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Times New Roman', Times, Georgia, serif;
  font-size: 12pt;
  line-height: 1.5;
  color: #1a1a1a;
  max-width: 8.5in;
  margin: 0 auto;
  padding: 0.75in;
  background: #fff;
}

/* --- Letterhead --- */
.letterhead {
  display: flex;
  align-items: flex-start;
  gap: 24px;
  border-bottom: 2px solid #1a3a5c;
  padding-bottom: 16px;
  margin-bottom: 32px;
}

.letterhead-info {
  flex: 1;
  text-align: right;
}

.firm-name {
  font-size: 18pt;
  font-weight: bold;
  color: #1a3a5c;
  letter-spacing: 0.5px;
}

.firm-details {
  font-size: 9pt;
  color: #555;
  line-height: 1.4;
  margin-top: 4px;
}

/* --- Date & Address --- */
.date-block {
  margin-bottom: 24px;
}

.recipient-block {
  margin-bottom: 24px;
  line-height: 1.4;
}

/* --- Salutation & Body --- */
.salutation {
  margin-bottom: 16px;
}

.re-line {
  font-weight: bold;
  margin-bottom: 16px;
}

.body p {
  margin-bottom: 12px;
  text-align: justify;
}

.section-title {
  font-weight: bold;
  text-decoration: underline;
  margin-top: 20px;
  margin-bottom: 8px;
}

/* --- Signature --- */
.closing {
  margin-top: 32px;
  margin-bottom: 48px;
}

.signature-line {
  border-bottom: 1px solid #1a1a1a;
  width: 300px;
  margin-bottom: 4px;
}

.signature-name {
  font-weight: bold;
}

/* --- Footer --- */
.footer {
  margin-top: 48px;
  text-align: center;
  font-size: 8pt;
  color: #999;
  border-top: 1px solid #ddd;
  padding-top: 8px;
}

@media print {
  body {
    padding: 0;
    margin: 0;
  }
}
```

---

## Document Structure

Every letter must follow this HTML structure:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Document Title</title>
  <style>
    /* Paste the full CSS template above here */
  </style>
</head>
<body>

  <!-- Letterhead -->
  <div class="letterhead">
    <div class="letterhead-info">
      <div class="firm-name">[Firm/Company Name]</div>
      <div class="firm-details">
        [Address Line 1]<br>
        [City, State ZIP]<br>
        Tel: [Phone] &bull; [Email]
      </div>
    </div>
  </div>

  <!-- Date -->
  <div class="date-block">[Month Day, Year]</div>

  <!-- Recipient -->
  <div class="recipient-block">
    [Recipient Name]<br>
    [Street Address]<br>
    [City, State ZIP]
  </div>

  <!-- Salutation -->
  <div class="salutation">Dear [Name]:</div>

  <!-- Re: line (optional) -->
  <div class="re-line">Re: [Subject Matter]</div>

  <!-- Body -->
  <div class="body">
    <p>[Opening paragraph — state the purpose of the letter.]</p>

    <div class="section-title">[Section Title]</div>
    <p>[Content...]</p>

    <div class="section-title">[Section Title]</div>
    <p>[Content...]</p>

    <p>[Closing paragraph — next steps, call to action.]</p>
  </div>

  <!-- Closing -->
  <div class="closing">[Sincerely / Respectfully / Very truly yours,]</div>

  <!-- Signature -->
  <div class="signature-line"></div>
  <div class="signature-name">[Signer Name]</div>
  <div>[Title / Organization]</div>

  <!-- Footer -->
  <div class="footer">
    [CONFIDENTIALITY NOTICE]
  </div>

</body>
</html>
```

---

## Content Rules

1. **No JavaScript.** Do not include `<script>` tags. The iframe blocks script execution — they won't run anyway, and including them may cause validation issues.

2. **Inline all CSS.** Use a single `<style>` block in `<head>`. Do not reference external stylesheets — they won't load in the sandboxed iframe.

3. **No external images.** Do not use `<img src="...">` with external URLs. If a logo is needed, note it with a placeholder comment `<!-- Logo: [description] -->`.

4. **Real data only.** Populate the letter with actual data from the case — company name from profile, recipient name from parties, dates and amounts from documents.

5. **Cite sources.** When referencing facts, include the document name or block ID in an HTML comment: `<!-- Source: doc_credit_001, block 452 -->`.

---

## Anti-Patterns

| Don't | Do Instead |
|-------|-----------|
| Use `html` for data tables or checklists | Use `json_view` with table or list viewType |
| Reference external CSS files | Embed all CSS in a `<style>` block |
| Include `<script>` tags | HTML is script-free by design |
| Use inline styles (`style="..."`) | Use CSS classes from the template |
| Invent company information | Pull from company profile via `get_case_profile` |
| Write in markdown and wrap in HTML | Write semantic HTML with the template structure |
