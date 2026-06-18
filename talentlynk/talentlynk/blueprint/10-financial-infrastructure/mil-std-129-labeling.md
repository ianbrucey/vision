# MIL-STD-129 Labeling

## Purpose
Generate Military Standard 129 (MIL-STD-129) compliant shipping labels for product shipments to DoD depots. These labels are a mandatory part of the DoD supply chain — shipments without proper MIL-STD-129 labels are rejected at the receiving dock.

## What MIL-STD-129 Requires

MIL-STD-129 prescribes the format, content, and placement of markings on military shipments. Key requirements:
- **National Stock Number (NSN)** or NATO Stock Number
- **Contract Number** and Delivery Order number
- **Shipment Number** (sequential per contract)
- **Ultimate Consignee** (destination depot and DoDAAC)
- **Weight and Cube** (dimensional data)
- **Date Shipped**
- **Serial Numbers** (if applicable)
- **RFID Tag** (if required by DFARS 252.211-7006 — passive RFID at the case/pallet level)
- **Barcode:** Linear (Code 39) or 2D (PDF417) encoding of key data

## Label Formats

### Standard Label
- Size: 6" × 4" (standard label) or larger as needed
- Data elements in prescribed layout
- Human-readable + machine-readable (barcode)

### RFID Tag (DFARS 252.211-7006)
- Passive UHF RFID tag (EPC Gen 2)
- Encoded with unique item identifier (UII) or shipment data
- Affixed to shipping container or pallet

## System Behavior

### Auto-Generation
- Trigger: product subcontractor ready to ship
- System pulls: contract number, NSN (if supplied), destination DoDAAC, shipment details
- Generates: compliant MIL-STD-129 label PDF
- Subcontractor downloads and affixes to shipment

### Label Data Population
```
Label Data:
  Contract Number: W912HN-24-C-0001
  Delivery Order: 0001
  Shipment Number: 001
  NSN: 8465-01-234-5678 (if applicable)
  Nomenclature: Pouch, First Aid, Individual
  Quantity: 1,000 units
  Weight: 250 lbs
  Cube: 12.5 cu ft
  Origin: TexShield Fabrics, 123 Industrial Dr, Austin, TX
  Consignee: DLA Distribution Depot, DoDAAC: SW3121
  Date Shipped: 2026-10-15
  RFID Tag ID: (auto-assigned)
```

### DD Form 250 Integration
- MIL-STD-129 labels are often accompanied by DD Form 250 (Material Inspection and Receiving Report)
- System can generate DD 250 data alongside labels

## Dependencies
- [[../11-product-acquisition/]]
- [[../09-post-award/wawf-ipp-invoicing]]

## Key Rules & Compliance
- MIL-STD-129R (current revision): Military Marking for Shipment and Storage
- DFARS 252.211-7006: Passive RFID tagging (for applicable items/contracts)
- DFARS 252.211-7003: Item Unique Identification and Valuation (IUID/UID)
- Incorrect labeling = rejected shipment = late delivery = potential contract penalty
- RFID requirements are contract-specific; not all DoD contracts require RFID

## Open Questions
- Should the system maintain the full MIL-STD-129 specification for auto-validation?
- Label generation: in-app PDF, or integration with a label printing service?
