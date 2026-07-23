#!/usr/bin/env python3
"""Parse DIBBS RFQ markdown files and produce a unified CSV."""
import csv
import re
import os
import glob

def extract_qty_pr(purchase_text):
    """Extract PR number and quantity from purchase request field."""
    text = purchase_text.strip()
    # Patterns like: "7017576208QTY: 1" or "7010782611QTY - See Solicitation"
    pr = ""
    qty = ""
    # Match PR (digits) followed by QTY
    m = re.match(r'(\d+)\s*QTY\s*(?:\\?[:=-])\s*(.+)$', text, re.IGNORECASE)
    if m:
        pr = m.group(1)
        qty = m.group(2).strip()
        # Try to extract numeric qty
        qm = re.match(r'(\d+)', qty)
        if qm:
            qty = qm.group(1)
    else:
        # Just digits?
        m2 = re.match(r'(\d+)', text)
        if m2:
            pr = m2.group(1)
    return pr, qty

def parse_solicitation(sol_text):
    """Clean solicitation text - remove » and 'Package View' stuff."""
    text = sol_text.strip()
    # Remove image references and package view suffixes
    text = re.sub(r'![^|]*', '', text)  # Remove image markdown
    text = re.sub(r'\[image\d+\]', '', text)
    text = re.sub(r'»\s*Package\s*View.*$', '', text).strip()
    return text

def parse_nsn_part(text):
    """Parse NSN/Part Number column. Returns (row_num, nsn, mil_spec)."""
    text = text.strip()
    mil_spec = ""
    if 'Mil-Spec' in text:
        mil_spec = "Mil-Spec"
        text = text.replace('Mil-Spec', '').strip()

    # Check if there's a row number prepended (e.g. "162 6240-01-475-8238")
    # Row numbers are 1-3 digits at start
    m = re.match(r'^(\d{1,3})\s+(.+)$', text)
    if m:
        # Check if the number looks like a row index (1-254) vs part of NSN
        num = m.group(1)
        rest = m.group(2)
        # If rest contains a proper NSN (with dashes) or is a part number,
        # the leading digits are likely the row #
        if re.search(r'\d{4}-\d{2}-\d{3}-\d{4}', rest) or re.search(r'^\d{4}[A-Z]?\d{4,}', rest):
            return num, rest, mil_spec
        # Otherwise treat the whole thing as NSN/part
        return '', text, mil_spec

    return '', text, mil_spec

def extract_rows_from_file(filepath):
    """Extract all data rows from a markdown file."""
    rows = []
    with open(filepath, 'r') as f:
        lines = f.readlines()

    in_table = False
    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            continue

        # Split by pipe
        cells = [c.strip() for c in line.split('|')]
        # Remove leading/trailing empty cells from pipe delimiters
        cells = [c for c in cells if c != '']
        # Or keep structure: first and last empty from | ... |
        # Actually let's keep all including empties and trim first/last
        cells = [c.strip() for c in line.split('|')]
        if cells and cells[0] == '':
            cells = cells[1:]
        if cells and cells[-1] == '':
            cells = cells[:-1]

        # Skip header rows, navigation rows, etc.
        if len(cells) < 7:
            continue

        # Skip known non-data rows
        row_text = ' '.join(cells)
        if any(skip in row_text for skip in [
            'Home', 'FAQ/Help', 'Navigation:', 'NSN/Part Number',
            'Policy Statements', 'Ver.6.3.2', 'Location:',
            'Records Found:', 'Click on Solicitation',
            'Notice:', 'Please read notices',
            '1 2 3 4 5 6', '#',
        ]):
            continue

        # Check if any cell contains an NSN-like pattern or part number
        has_nsn = False
        for c in cells:
            if re.search(r'\d{4}-\d{2}-\d{3}-\d{4}', c):
                has_nsn = True
                break
            # Part numbers like 0001S00000052
            if re.search(r'\d{4}[A-Z]\d{7,}', c):
                has_nsn = True
                break

        if not has_nsn:
            continue

        # Now parse the row
        # We need: row_num, nsn, nomenclature, tech_docs, solicitation, status, purchase_req, issued, return_by
        # The cells might be shifted

        # Case 1: 9 cells (standard): # | NSN | Nomenclature | Tech Docs | Solicitation | Status | PR | Issued | Return By
        # Case 2: 8 cells: # and NSN merged in cell[0] | Nomenclature | Tech Docs | ...

        row_num = ''
        nsn = ''
        mil_spec = ''
        nomenclature = ''
        tech_docs = ''
        solicitation = ''
        status = ''
        purchase_req = ''
        issued = ''
        return_by = ''

        if len(cells) == 9:
            # Standard: cells[0]=#, cells[1]=NSN, cells[2]=Nomenclature, cells[3]=TechDocs,
            # cells[4]=Solicitation, cells[5]=Status, cells[6]=PR, cells[7]=Issued, cells[8]=ReturnBy
            row_num = cells[0].strip()
            nsn_raw = cells[1].strip()
            row_num2, nsn, mil_spec = parse_nsn_part(nsn_raw)
            if row_num2 and not row_num:
                row_num = row_num2
            nomenclature = cells[2].strip()
            tech_docs = cells[3].strip()
            solicitation = parse_solicitation(cells[4])
            status = cells[5].strip()
            purchase_req = cells[6].strip()
            issued = cells[7].strip()
            return_by = cells[8].strip()
        elif len(cells) == 8:
            # # merged with NSN in cells[0]
            nsn_raw = cells[0].strip()
            row_num, nsn, mil_spec = parse_nsn_part(nsn_raw)
            nomenclature = cells[1].strip()
            tech_docs = cells[2].strip()
            solicitation = parse_solicitation(cells[3])
            status = cells[4].strip()
            purchase_req = cells[5].strip()
            issued = cells[6].strip()
            return_by = cells[7].strip()
        else:
            # Try to figure it out from cell content
            # Find the cell with NSN
            nsn_idx = None
            for i, c in enumerate(cells):
                if re.search(r'\d{4}-\d{2}-\d{3}-\d{4}', c):
                    nsn_idx = i
                    break
                if re.search(r'\d{4}[A-Z]\d{7,}', c):
                    nsn_idx = i
                    break
            if nsn_idx is None:
                continue

            nsn_raw = cells[nsn_idx].strip()
            if nsn_idx > 0:
                row_num = cells[nsn_idx - 1].strip() if cells[nsn_idx - 1].strip().isdigit() else ''
            row_num2, nsn, mil_spec = parse_nsn_part(nsn_raw)
            if row_num2 and not row_num:
                row_num = row_num2

            remaining = cells[nsn_idx + 1:]
            if len(remaining) >= 6:
                nomenclature = remaining[0]
                tech_docs = remaining[1]
                solicitation = parse_solicitation(remaining[2])
                status = remaining[3]
                purchase_req = remaining[4]
                issued = remaining[5] if len(remaining) > 5 else ''
                return_by = remaining[6] if len(remaining) > 6 else ''

        # Skip if no NSN
        if not nsn:
            continue

        # Clean up status
        status = 'Open'  # All are Open

        # Extract PR and QTY
        pr, qty = extract_qty_pr(purchase_req)

        # Clean NSN - remove trailing commas
        nsn = nsn.rstrip(',')

        rows.append({
            'row_num': row_num,
            'nsn': nsn,
            'mil_spec': mil_spec,
            'nomenclature': nomenclature,
            'tech_docs': tech_docs,
            'solicitation': solicitation,
            'status': status,
            'purchase_request': pr,
            'qty': qty,
            'issued': issued,
            'return_by': return_by,
        })

    return rows

def main():
    md_dir = os.path.dirname(os.path.abspath(__file__)) + '/markdown'
    files = sorted(glob.glob(os.path.join(md_dir, '*DIBBS*.md')))

    all_rows = []
    seen = set()  # deduplicate by solicitation+nsn+pr

    for f in files:
        rows = extract_rows_from_file(f)
        for r in rows:
            key = (r['solicitation'], r['nsn'], r['purchase_request'])
            if key not in seen:
                seen.add(key)
                all_rows.append(r)

    # Sort by row_num if numeric
    def sort_key(r):
        try:
            return int(r['row_num'])
        except ValueError:
            return 9999

    all_rows.sort(key=sort_key)

    # Write CSV
    outpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dibbs_rfq_unified.csv')
    with open(outpath, 'w', newline='') as csvfile:
        fieldnames = [
            'row_num', 'nsn', 'mil_spec', 'nomenclature', 'tech_docs',
            'solicitation', 'status', 'purchase_request', 'qty', 'issued', 'return_by'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in all_rows:
            writer.writerow(r)

    print(f"Extracted {len(all_rows)} unique rows from {len(files)} files.")
    print(f"Output: {outpath}")

    # Print summary counts
    nsn_count = len(set(r['nsn'] for r in all_rows))
    sol_count = len(set(r['solicitation'] for r in all_rows))
    print(f"Unique NSNs: {nsn_count}")
    print(f"Unique Solicitations: {sol_count}")

if __name__ == '__main__':
    main()
