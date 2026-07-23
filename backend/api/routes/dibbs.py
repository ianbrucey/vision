"""Vision — DIBBS RFQ Opportunities API Routes."""

from __future__ import annotations

import csv, io, uuid
from io import StringIO
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from auth import get_current_user
from core.db import connect, tx

router = APIRouter(prefix="/api/dibbs", tags=["dibbs"])

_SORTABLE = {"nomenclature","nsn","solicitation","qty","issued","return_by","status"}


@router.post("/upload")
async def upload_dibbs_csv(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Must be a .csv")
    text = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames: raise HTTPException(400, "CSV has no headers")

    batch_id = str(uuid.uuid4())
    buf = StringIO()
    db_cols = ["row_num","nsn","mil_spec","nomenclature","tech_docs","solicitation","status","purchase_request","qty","issued","return_by","fsc_code","upload_batch_id","source_file"]
    rows_written = 0
    for row in reader:
        nsn = (row.get("nsn") or "").strip()
        fsc = nsn[:4] if nsn and "-" in nsn else ""
        vals = [row.get("row_num","") or "0", nsn, row.get("mil_spec",""), row.get("nomenclature","(no title)"),
                row.get("tech_docs",""), row.get("solicitation",""), row.get("status","Open"),
                row.get("purchase_request",""), row.get("qty","0"), row.get("issued",""), row.get("return_by",""),
                fsc, batch_id, file.filename]
        buf.write("\t".join(v.replace("\\","\\\\").replace("\t"," ") if v else "\\N" for v in vals) + "\n")
        rows_written += 1

    with tx() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE TEMP TABLE IF NOT EXISTS _dibbs_import (LIKE dibbs_rfqs INCLUDING DEFAULTS) ON COMMIT DROP")
            cur.execute("DELETE FROM _dibbs_import")
            buf.seek(0)
            cur.copy_from(buf, "_dibbs_import", sep="\t", null="\\N", columns=db_cols)
            cur.execute("""INSERT INTO dibbs_rfqs (row_num,nsn,mil_spec,nomenclature,tech_docs,solicitation,status,purchase_request,qty,issued,return_by,fsc_code,upload_batch_id,source_file)
                SELECT row_num,nsn,mil_spec,nomenclature,tech_docs,solicitation,status,purchase_request,qty,issued,return_by,fsc_code,upload_batch_id,source_file
                FROM _dibbs_import ON CONFLICT (solicitation) DO NOTHING""")
            inserted = cur.rowcount
    return {"batch_id":batch_id,"rows_imported":rows_written,"rows_inserted":inserted,"source":file.filename}


class DibbsQuery(BaseModel):
    q: str|None=None; nsn: str|None=None; fsc_code: str|None=None; solicitation: str|None=None
    status: str|None=None; limit: int=100; offset: int=0; order_by: str="return_by"; order_dir: str="ASC"


@router.post("/query")
def query_dibbs(body: DibbsQuery, user: dict = Depends(get_current_user)):
    conn = connect()
    try:
        with conn.cursor() as cur:
            where=[]; params=[]
            if body.q and body.q.strip():
                w=body.q.strip().split()
                if len(w)==1: where.append("search_vector @@ plainto_tsquery('english',%s)"); params.append(w[0])
                else: where.append(f"search_vector @@ ({' || '.join(['plainto_tsquery(%s)']*len(w))})"); params.extend(w)
            for col,val,m in [("nsn",body.nsn,"exact"),("fsc_code",body.fsc_code,"exact"),("solicitation",body.solicitation,"exact"),("status",body.status,"exact")]:
                if val and val.strip():
                    where.append(f"{col}={'=' if m=='exact' else 'ILIKE'} %s")
                    params.append(val.strip() if m=="exact" else f"%{val.strip()}%")
            wc="WHERE "+" AND ".join(where) if where else ""
            oc=body.order_by if body.order_by in _SORTABLE else "return_by"
            od="ASC" if body.order_dir.upper()=="ASC" else "DESC"
            lim=min(body.limit,1000); off=max(body.offset,0)
            cur.execute(f"SELECT COUNT(*) FROM dibbs_rfqs {wc}",tuple(params))
            total=cur.fetchone()[0]
            cur.execute(f"SELECT * FROM dibbs_rfqs {wc} ORDER BY {oc} {od} LIMIT %s OFFSET %s",tuple(params+[lim,off]))
            rows=cur.fetchall(); cols=[d[0] for d in cur.description]
            return {"total":total,"limit":lim,"offset":off,"count":len(rows),"results":[dict(zip(cols,r)) for r in rows]}
    finally: conn.close()


@router.delete("/all")
def delete_all(user: dict = Depends(get_current_user)):
    with tx() as conn:
        with conn.cursor() as cur: cur.execute("DELETE FROM dibbs_rfqs"); return {"deleted":cur.rowcount}
