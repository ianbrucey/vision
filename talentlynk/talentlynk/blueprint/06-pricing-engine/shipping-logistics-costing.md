# Shipping & Logistics Costing

## Purpose
Calculate shipping, freight, and logistics costs for product supply contracts. Handles MIL-STD-129 labeling requirements for DoD shipments and factors freight into the total bid price.

## Inputs
- Product details (dimensions, weight, quantity, hazardous materials)
- Shipping origin (manufacturer facility) and destination (government depot/site)
- Required delivery timeline
- MIL-STD-129 requirements (if DoD contract)

## Outputs
- Estimated shipping cost
- Recommended shipping method
- MIL-STD-129 labeling requirements flag
- Total logistics line item for bid pricing

## Costing Methods

### Standard Commercial Freight
- LTL (Less Than Truckload) for smaller shipments
- FTL (Full Truckload) for large shipments
- Parcel (UPS/FedEx) for small, light items
- System estimates using dimensional weight + distance

### Military Shipments (DoD)
- **MIL-STD-129:** Military Standard for Shipping and Storage Marks
- Requires specific labeling: NSN, contract number, destination, weight, cube
- RFID tags may be required (DFARS 252.211-7006)
- DD Form 250 (Material Inspection and Receiving Report)

### FOB Terms
- **FOB Origin:** Government pays freight; contractor delivers to carrier; contractor's responsibility ends at origin
- **FOB Destination:** Contractor pays freight; contractor responsible until delivery at government site
- System must check solicitation for FOB terms and include/exclude freight accordingly

## System Behavior

### Auto-Estimation
- Pull product weight/dimensions from manufacturer profile
- Pull origin (manufacturer address) and destination (solicitation delivery location)
- Query freight rate APIs or use stored rate tables
- Calculate estimated freight cost

### MIL-STD-129 Detection
- If solicitation is DoD: auto-flag MIL-STD-129 requirement
- Generate compliant label template
- Include labeling cost in bid (labor to label + label materials)

### Freight Line Item
- Shipping presented as a separate CLIN (Contract Line Item Number) or included in unit price per solicitation instructions
- Some solicitations require FOB Destination — freight is baked into unit price, not a separate line

## Dependencies
- [[cost-estimation-formula]]
- [[../11-product-acquisition/]]
- [[../02-onboarding/manufacturer-onboarding]]

## Key Rules & Compliance
- FOB terms: FAR 47.3 — Transportation provisions
- MIL-STD-129: mandatory for DoD shipments
- DFARS 252.211-7006: Passive RFID tagging (if applicable)
- Freight costs must be "fair and reasonable" — supporting quotes may be required

## Open Questions
- Integrate with live freight rate APIs, or use static rate tables?
- Should the system generate MIL-STD-129 labels automatically?
