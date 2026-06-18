# AcroForm Filler

## Purpose
Programmatically fill interactive government PDF forms (those with embedded AcroForm fields) by mapping field names to data sources and injecting values directly into the form fields. This is the fast, reliable path — no computer vision needed.

## Inputs
- Interactive PDF form (detected by [[pdf-form-detection]])
- Mapped field names from the form
- Data sources: entity profile, vendor profile, solicitation data, pricing data

## Outputs
- Filled PDF with all mapped fields populated
- Fields-filled audit: which fields were filled, which were left blank
- Flag: any required fields without matching data

## How It Works

### 1. Field Name Extraction
Read the PDF's internal field dictionary:
```
Field: "Form_1_Company_Name" → Position: (72, 620)
Field: "Form_1_UEI" → Position: (400, 620)
Field: "Form_1_Total_Price" → Position: (400, 100)
```

### 2. Field-to-Data Mapping
Map each form field to a data source:
```
"Form_1_Company_Name" → entity.companyName
"Form_1_UEI" → entity.uei
"Form_1_Total_Price" → bid.totalPrice
"Form_1_Signature" → (digital signature placeholder)
```

Field-to-data mappings are maintained in a template library:
```json
{
  "formTemplate": "SF-1449",
  "mappings": [
    {"fieldName": "Form_1_Company_Name", "dataPath": "entity.companyName"},
    {"fieldName": "Form_1_UEI", "dataPath": "entity.uei"},
    {"fieldName": "Form_1_CAGE", "dataPath": "entity.cageCode"},
    {"fieldName": "Form_1_NAICS", "dataPath": "solicitation.primaryNaics"},
    {"fieldName": "Form_1_Total_Price", "dataPath": "bid.totalPrice", "format": "currency"}
  ]
}
```

### 3. Data Injection
- For each mapped field, resolve the data path to an actual value
- Inject the value into the form field
- Handle field constraints: max length, font size, character restrictions
- Checkbox fields: set checked/unchecked based on boolean data

### 4. Validation
- Check all "required" fields have values
- Check field lengths don't exceed capacity
- Flag unmapped required fields: "No data source for field 'Form_1_XYZ'"

## Template Library

The system maintains a growing library of known government forms and their field mappings:
- **SF-1449:** Solicitation/Contract/Order for Commercial Items
- **SF-1442:** Solicitation, Offer, and Award (Construction)
- **SF-30:** Amendment of Solicitation
- **SF-LLL:** Disclosure of Lobbying Activities
- **FAR 52.212-3:** Offeror Representations and Certifications (if fillable PDF provided)
- **Agency-specific forms:** As encountered and mapped

First time a new form is encountered: manual mapping required → saved to template library → auto-fill available for future bids.

## Dependencies
- [[pdf-form-detection]]
- [[../01-corporate-foundation/sam-registration]]
- [[../01-corporate-foundation/entity-structure]]
- [[../06-pricing-engine/cost-estimation-formula]]

## Key Rules & Compliance
- Do NOT modify the form's layout, clauses, or structure — fill fields only
- Do NOT leave mandatory fields empty
- Signed forms are legally binding — ensure accuracy before signature
- Some forms have hidden calculation fields — do not override them

## Open Questions
- Template library: stored in database or as configuration files?
- How to handle forms with dynamic/repeating sections (e.g., multiple CLIN pricing rows)?
