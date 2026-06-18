# Computer Vision Form Filler

## Purpose
Fill flattened or scanned government PDF forms using Document Layout Analysis (DLA) and computer vision. When a PDF has no interactive AcroForm fields and no extractable text layer, this pipeline locates fillable regions via bounding box detection and programmatically overlays text at the correct coordinates.

## The Four-Step Pipeline

### Step 1: Bounding Box Detection
Convert the PDF page to a high-resolution image. Using object detection (OpenCV contour mapping, Vision-Language Model, or specialized layout parser), locate visual form elements:

- **Bordered boxes:** Traced rectangles representing input cells
- **Horizontal lines:** Solid lines adjacent to text labels (blank fields)
- **Checkboxes:** Small square matrices near `[ ] Yes  [ ] No` style options
- **Signature blocks:** Large bordered or blank areas

### Step 2: Coordinate Mapping & Classification
Every detected field is wrapped in a Bounding Box with precise spatial grid coordinates:
```
Field: { label: "CAGE Code:", type: "text", bbox: [398, 618, 502, 642], page: 1 }
Field: { label: "Small Business", type: "checkbox", bbox: [100, 500, 115, 515], page: 1 }
Field: { label: "Signature", type: "signature", bbox: [300, 150, 500, 200], page: 3 }
```

Coordinate mapping is expressed as pixel coordinates: `[X-Start, Y-Start, X-End, Y-End]` from page margins.

### Step 3: Contextual Alignment (Label-to-Field Pairing)
The AI reads text labels adjacent to each detected field to determine what data goes there:
- Detects text label "CAGE Code:" → maps to `entity.cageCode`
- Detects text label "Total Proposed Price:" → maps to `bid.totalPrice`
- Detects "NAICS Code:" → maps to `entity.primaryNaics`

This is the hardest step — labels can be above, to the left, below, or inline with the field. The CV model must correctly associate labels with their fields.

### Step 4: Programmatic Overlay & Text Injection
Using a PDF manipulation API or writing engine:
- Place text at the exact `[X, Y]` coordinate within the bounding box
- Apply font size, alignment, and styling
- **Auto-scaling guardrail:** If company name is too long for the detected box width, auto-shrink font size to fit (see [[text-auto-scaling]])
- Render checkbox marks, signatures (image overlay), and other non-text elements

## Technical Architecture

```
[Scanned PDF] → [Page → Image conversion (300 DPI)]
    → [Object Detection Model: locate form fields]
    → [OCR: read adjacent labels]
    → [Field Classification: text, checkbox, signature]
    → [Label-to-Data Mapping]
    → [Text Rendering with auto-scaling]
    → [Overlay onto original PDF page]
    → [Flatten to final PDF (no residual layers)]
```

## Visual Reference

A typical SF-1449 form page has:
- Block 1-2: Solicitation/Contract number (pre-filled by government)
- Block 10: NAICS code
- Block 12: Discount terms
- Block 17: Contractor/Offeror info (NAME, UEI, CAGE, TIN)
- Block 19-24: Offer/Signature blocks
- Continuation pages: CLIN pricing schedule (tabular)

Each of these blocks contains multiple fields — the CV pipeline must detect and classify each one individually.

## Dependencies
- [[pdf-form-detection]]
- [[text-auto-scaling]]
- [[acroform-filler]] (for hybrid documents)

## Key Rules & Compliance
- Overlaid text must NOT cover or obscure any original form text or clauses
- Text must be clearly legible (minimum ~8pt after auto-scaling)
- Checkboxes must be clearly marked (solid fill or X, not ambiguous)
- The final PDF must be flattened — no residual editable layers
- CO must be able to read every field clearly; unclear entries = potential rejection

## Open Questions
- CV model: fine-tuned layout parser (e.g., LayoutLMv3), or general-purpose VL model?
- DPI for rendering: 300 DPI standard for OCR accuracy?
- How to handle forms with lines/boxes that are broken or partially obscured in the scan?
