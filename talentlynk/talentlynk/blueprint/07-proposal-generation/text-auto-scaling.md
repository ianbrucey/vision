# Text Auto-Scaling

## Purpose
Dynamically adjust font size to fit injected text within the detected bounding box of a government form field. If a company name is too long for the field width, the system shrinks the font so the text stays inside the lines — preventing overflow that looks unprofessional and could make data illegible to the Contracting Officer.

## Inputs
- Text string to inject (e.g., company name, address)
- Bounding box dimensions: `[x_start, y_start, x_end, y_end]`
- Base font size (default, e.g., 10pt or 12pt)
- Minimum allowed font size (e.g., 7pt — below this is likely illegible when printed)

## Outputs
- Adjusted font size
- Possibly: multi-line break if text is very long and box is tall enough
- Overflow warning if text cannot fit even at minimum font size

## Algorithm

```
function calculateFontSize(text, bbox, baseFontSize, minFontSize):
    boxWidth = bbox.x_end - bbox.x_start
    boxHeight = bbox.y_end - bbox.y_start

    fontSize = baseFontSize
    while getTextWidth(text, fontSize) > boxWidth AND fontSize > minFontSize:
        fontSize -= 0.5

    if fontSize < minFontSize:
        // Try multi-line wrapping
        lines = wrapText(text, boxWidth, minFontSize)
        if lines.height <= boxHeight:
            return (minFontSize, lines)
        else:
            flagOverflow(text, bbox)

    return fontSize
```

## Scaling Constraints

| Parameter | Default | Notes |
|-----------|---------|-------|
| Base font size | 10pt-12pt | Varies by form; detected from original form text |
| Minimum font size | 7pt | Below 7pt is barely legible in print |
| Minimum line height | font size × 1.2 | Adequate spacing between multi-line entries |
| Alignment | Left-aligned | Unless form field is center-aligned (e.g., numeric fields) |

## Overflow Handling

If text cannot fit even at minimum font size:
1. Try abbreviation (e.g., "Atlanta Commercial Landscaping LLC" → "Atlanta Comm. Landscaping LLC")
2. Try multi-line wrapping (if box height allows)
3. Flag for manual review: "Field 'Company Name' overflow — text too long for bounding box"
4. Proposal Manager must manually shorten or approve alternative rendering

## Dependencies
- [[computer-vision-form-filler]]
- [[acroform-filler]] (AcroForm fields also have width constraints)

## Key Rules & Compliance
- Illegible entries = non-compliant submission (CO won't guess)
- Text must be clearly readable when printed on standard letter paper
- Do not shrink so small that government scanning systems can't OCR the text

## Open Questions
- Should abbreviation rules be automated (with a lookup table of common abbreviations)?
- Font: should the system always match the form's original font, or is a standard sans-serif acceptable?
