# PDF Form Detection

## Purpose
Determine whether a government-provided PDF form is an interactive AcroForm (with embedded digital fields) or a flattened/scanned image PDF that requires computer vision to fill. This gate decision determines which filling pipeline to route the document through.

## Inputs
- Government PDF form (SF-1449, SF-30, agency-specific forms, etc.)
- Form context: what data needs to be filled into it

## Outputs
- Form type classification: Interactive (AcroForm) | Flattened (image-based) | Hybrid (some fields interactive, others not)
- Route: to [[acroform-filler]] or [[computer-vision-form-filler]]
- Field inventory (extracted fields for interactive; bounding boxes for flattened)

## Detection Logic

### Step 1: AcroForm Check
```python
# Check if PDF contains AcroForm fields
if pdf_has_acroform_fields(document):
    fields = extract_acroform_field_names(document)
    if len(fields) > 0:
        return "interactive", fields
```

### Step 2: Text Layer Check
```python
# Even if no AcroForm, check if PDF has extractable text
if pdf_has_text_layer(document):
    return "flattened_with_text", None
```

### Step 3: Image-Only Check
```python
# No AcroForm, no text layer → scanned image
if is_image_only(document):
    return "scanned_image", None
```

### Step 4: Hybrid Detection
Some government PDFs have partial AcroForms — a few fillable fields mixed with scanned pages. System must handle page-by-page:
- Page 1: interactive (AcroForm fields present)
- Page 2: scanned image (no fields, no text)
- Route each page appropriately

## Form Field Inventory

### For Interactive PDFs
```json
{
  "formType": "SF-1449",
  "detectionMethod": "acroform",
  "fields": [
    {"name": "Form_1_Company_Name", "type": "text", "page": 1, "rect": [72, 620, 350, 640]},
    {"name": "Form_1_UEI", "type": "text", "page": 1, "rect": [400, 620, 500, 640]},
    {"name": "Form_1_Checkbox_SmallBusiness", "type": "checkbox", "page": 1, "rect": [100, 500, 115, 515]}
  ]
}
```

### For Flattened PDFs
```json
{
  "formType": "SF-1449",
  "detectionMethod": "computer_vision",
  "fields": [
    {"label": "Company Name", "type": "text", "page": 1, "bbox": [72, 618, 352, 642], "fontSize": 10},
    {"label": "UEI", "type": "text", "page": 1, "bbox": [398, 618, 502, 642], "fontSize": 10}
  ]
}
```

## System Behavior

### Auto-Routing
- Interactive PDF → fast path (field name matching, no CV needed)
- Flattened/scanned PDF → CV pipeline ([[computer-vision-form-filler]])
- Hybrid → split processing (page-by-page routing)

### Unknown Form Handling
- Form not in template library? → attempt auto-detection
- Auto-detection fails? → flag for manual form setup (first time only; saved as template)

## Dependencies
- [[acroform-filler]]
- [[computer-vision-form-filler]]
- [[text-auto-scaling]]

## Key Rules & Compliance
- Government forms must be reproduced exactly — no altering layout, no removing clauses
- Field detection errors = misaligned text = unprofessional, potentially non-compliant submission
- Some forms contain barcodes or QR codes that encode filled data — system must not break these

## Open Questions
- Preferred CV model for bounding box detection?
- Should the system maintain a template library of "known" government forms for faster detection?
