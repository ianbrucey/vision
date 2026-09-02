"""Fill SF 1449 blocks for NOAA RFQ 1305M326Q0368 (Justice Quest LLC quote)."""
import pymupdf

SRC = "/Users/admin/code/vision/.claude/skills/sources-sought-response/actual_notices/B--Senior C++ programmer to modify the COMPASS model /Sol_1305M326Q0368.pdf"
OUT = "/Users/admin/code/vision/.claude/skills/sources-sought-response/responses/1305M326Q0368-compass/Sol_1305M326Q0368_filled.pdf"

doc = pymupdf.open(SRC)
BLACK = (0, 0, 0)


def put(page, text, x, y, size=8, right=None):
    """Insert text; right-align when `right` edge coordinate given."""
    if right is not None:
        w = pymupdf.get_text_length(text, fontname="helv", fontsize=size)
        x = right - w
    page.insert_text((x, y), text, fontsize=size, fontname="helv", color=BLACK)


p1, p2, p3 = doc[0], doc[1], doc[2]

# Block 12 — DISCOUNT TERMS (blank sits left of "12." label at x0=138.3, y0=216.4)
put(p1, "Net 30", 0, 218.5, right=136.5)

# Block 17a — name / address / UEI lines (below OFFEROR label y=351.5, above TELEPHONE y=410)
put(p1, "Justice Quest LLC (dba Vision Systems)", 45.8, 363.5)
put(p1, "267 Langley Dr. #1267, Lawrenceville, GA 30046", 45.8, 375.0)
put(p1, "UEI: MU8FAL4JBL91  CAGE: 21GM9", 45.8, 386.5)
# Telephone number (right of "TELEPHONE NUMBER" label ending x=104.9, y=410)
put(p1, "(470) 785-3007", 110, 410.0)

# CLIN 0001 row (page 1): "0001" at x0=43.8, y0=513.9 -> price row baseline ~516
put(p1, "$41,250.00", 0, 516.0, size=7.5, right=525)   # col 23 UNIT PRICE
put(p1, "$41,250.00", 0, 516.0, size=7.5, right=574)   # col 24 AMOUNT

# CLIN 1001 row (page 2): "1001" at x0=36.3, y0=210.7 -> price row baseline ~213
put(p2, "$41,250.00", 0, 213.0, size=7.5, right=515)
put(p2, "$41,250.00", 0, 213.0, size=7.5, right=574)

# CLIN 2001 row (page 3, OF 336): "2001" at x0=32.3, y0=121.7 -> price row baseline ~124.5
put(p3, "$41,250.00", 0, 124.5, size=7.5, right=517)
put(p3, "$41,250.00", 0, 124.5, size=7.5, right=574)

# Block 30a/b/c — signature block (labels at y=664.8 and y=695.4)
put(p1, "Ian Bruce", 48.0, 657.0)
put(p1, "Ian Bruce, Principal Engineer & Founder", 48.0, 688.5)
put(p1, "08/21/2026", 240.5, 688.5)

doc.save(OUT, deflate=True)
print("Saved:", OUT)
