"""
External Integration Tools for the Vision SDK Agent.

Ported from the war-room-1 MCP server (mcp-server/server.py) as in-process
SDK custom tools using the claude_agent_sdk @tool decorator.

Tool groups:
  - Research (GPT Researcher + Tavily): deep_research, quick_search,
    extract_page, write_report
  - Court Listener: search_cases, get_opinion, query_opinion,
    query_document, lookup_citation
  - Legal Brain (Neo4j): 12 knowledge graph tools for case ingestion,
    strategy analysis, and readiness assessment
"""

from __future__ import annotations

import asyncio
import base64
import json
import mimetypes
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from claude_agent_sdk import create_sdk_mcp_server, tool, ToolAnnotations

# ---------------------------------------------------------------------------
# Path setup — reach war-room-1 clients
# ---------------------------------------------------------------------------
_WAR_ROOM_MCP = Path("/Users/ianbruce/code/war-room-1/mcp-server")
if str(_WAR_ROOM_MCP) not in sys.path:
    sys.path.insert(0, str(_WAR_ROOM_MCP))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _result(data: dict | str) -> dict[str, Any]:
    """Wrap a dict or string as a standard SDK tool result."""
    text = json.dumps(data, default=str) if isinstance(data, dict) else data
    return {"content": [{"type": "text", "text": text}]}


def _error(message: str) -> dict[str, Any]:
    """Return an error result that Claude can react to."""
    return {"content": [{"type": "text", "text": message}], "is_error": True}


# ===================================================================
# RESEARCH TOOLS (GPT Researcher + Tavily)
# ===================================================================

def _get_tavily_client():
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return None
    from tavily import TavilyClient
    return TavilyClient(api_key=api_key)


@tool(
    "deep_research",
    "Conduct comprehensive research on a topic using GPT Researcher. "
    "Returns research data and source URLs. Use for deep, multi-source "
    "investigations where surface-level search is insufficient.",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The research question or topic."},
            "report_type": {
                "type": "string",
                "enum": ["research_report", "detailed_report", "quick_report"],
                "description": "Type of report. Default: research_report.",
            },
            "max_sources": {
                "type": "integer",
                "description": "Maximum number of sources to use. Default: 10.",
            },
        },
        "required": ["query"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def deep_research(args: dict[str, Any]) -> dict[str, Any]:
    try:
        from gpt_researcher import GPTResearcher

        query = args["query"]
        report_type = args.get("report_type", "research_report")
        researcher = GPTResearcher(query=query, report_type=report_type)
        research_data = await researcher.conduct_research()
        sources = (
            researcher.get_source_urls()
            if hasattr(researcher, "get_source_urls")
            else []
        )
        return _result({"research_data": research_data, "sources": sources})
    except Exception as exc:
        return _error(f"deep_research failed: {exc}")


@tool(
    "quick_search",
    "Perform a quick web search using Tavily. Returns URLs, titles, "
    "content snippets, and an AI-generated answer if available. "
    "Use for fast fact-checking and surface-level queries.",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query."},
            "max_results": {
                "type": "integer",
                "description": "Maximum results. Default: 5.",
            },
        },
        "required": ["query"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def quick_search(args: dict[str, Any]) -> dict[str, Any]:
    try:
        client = _get_tavily_client()
        if not client:
            return _error("TAVILY_API_KEY is not configured")
        response = await asyncio.to_thread(
            client.search, args["query"], max_results=args.get("max_results", 5)
        )
        return _result({
            "query": args["query"],
            "answer": response.get("answer"),
            "results": response.get("results", []),
        })
    except Exception as exc:
        return _error(f"quick_search failed: {exc}")


@tool(
    "extract_page",
    "Extract the full text content of a webpage using Tavily. "
    "Use after quick_search to retrieve full text of a promising URL — "
    "especially for statutes, case opinions, and regulatory text.",
    {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Full URL of the page to extract."},
        },
        "required": ["url"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def extract_page(args: dict[str, Any]) -> dict[str, Any]:
    try:
        client = _get_tavily_client()
        if not client:
            return _error("TAVILY_API_KEY is not configured")
        response = await asyncio.to_thread(client.extract, args["url"])
        results = response.get("results", [])
        failed = response.get("failed_results", [])
        if results:
            return _result({
                "url": args["url"],
                "raw_content": results[0].get("raw_content", ""),
                "failed_urls": [r.get("url") for r in failed],
            })
        return _result({
            "url": args["url"],
            "raw_content": "",
            "failed_urls": [r.get("url") for r in failed],
            "error": "No content extracted",
        })
    except Exception as exc:
        return _error(f"extract_page failed: {exc}")


@tool(
    "write_report",
    "Generate a formatted research report from raw research data. "
    "Use after deep_research to produce a polished, structured report.",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Original research question."},
            "research_data": {"type": "string", "description": "Raw research data."},
            "report_type": {
                "type": "string",
                "enum": ["research_report", "detailed_report", "quick_report"],
                "description": "Report format. Default: research_report.",
            },
        },
        "required": ["query", "research_data"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def write_report(args: dict[str, Any]) -> dict[str, Any]:
    try:
        from gpt_researcher import GPTResearcher

        researcher = GPTResearcher(
            query=args["query"],
            report_type=args.get("report_type", "research_report"),
        )
        researcher.context = args["research_data"]
        report = await researcher.write_report()
        return _result({"report": report})
    except Exception as exc:
        return _error(f"write_report failed: {exc}")


# ===================================================================
# COURT LISTENER TOOLS
# ===================================================================

def _get_court_listener_client() -> "CourtListenerClient":
    return CourtListenerClient()


class CourtListenerClient:
    """Lightweight async Court Listener API client."""

    def __init__(self):
        self.base_url = os.getenv(
            "COURT_LISTENER_BASE_URL", "https://www.courtlistener.com/api/rest/v4"
        )
        self.token = os.getenv("COURT_LISTENER_API_KEY", "")
        self.timeout = float(os.getenv("COURT_LISTENER_TIMEOUT", "30"))

    @property
    def headers(self) -> dict:
        return {"Authorization": f"Token {self.token}"} if self.token else {}

    async def get(self, endpoint: str, params: dict | None = None) -> dict:
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()

    async def post(self, endpoint: str, data: dict | None = None) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                data=data,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()


@tool(
    "search_cases",
    "Search legal cases by keyword, party name, or citation via Court "
    "Listener. Returns case name, court, date, docket number, and opinion "
    "ID for retrieving full text.",
    {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query — keyword, party name, or citation.",
            },
            "court": {
                "type": "string",
                "description": "Court filter, e.g. 'scotus', 'ca9'.",
            },
            "date_from": {
                "type": "string",
                "description": "Start date YYYY-MM-DD.",
            },
            "date_to": {
                "type": "string",
                "description": "End date YYYY-MM-DD.",
            },
            "max_results": {
                "type": "integer",
                "description": "Max results. Default: 10.",
            },
        },
        "required": ["query"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def search_cases(args: dict[str, Any]) -> dict[str, Any]:
    try:
        cl = _get_court_listener_client()
        params: dict[str, Any] = {
            "type": "o",
            "q": args["query"],
            "page_size": args.get("max_results", 10),
        }
        if args.get("court"):
            params["court"] = args["court"]
        if args.get("date_from"):
            params["filed_after"] = args["date_from"]
        if args.get("date_to"):
            params["filed_before"] = args["date_to"]

        raw = await cl.get("/search/", params)

        def _normalize(hit: dict) -> dict:
            opinions = hit.get("opinions") or []
            opinion_id = opinions[0].get("id") if opinions else None
            return {
                "opinion_id": opinion_id,
                "cluster_id": hit.get("cluster_id"),
                "case_name": hit.get("caseName") or hit.get("caseNameFull"),
                "court": hit.get("court"),
                "court_id": hit.get("court_id"),
                "date_filed": hit.get("dateFiled"),
                "citations": hit.get("citation", []),
                "docket_number": hit.get("docketNumber"),
                "judges": hit.get("judge"),
                "status": hit.get("status"),
                "snippet": opinions[0].get("snippet") if opinions else None,
            }

        normalized = [_normalize(r) for r in raw.get("results", [])]
        return _result({"results": normalized, "count": raw.get("count", 0)})
    except Exception as exc:
        return _error(f"search_cases failed: {exc}")


@tool(
    "get_opinion",
    "Retrieve the full text of a legal opinion by its Court Listener "
    "opinion ID. Use after search_cases to read the complete opinion.",
    {
        "type": "object",
        "properties": {
            "opinion_id": {
                "type": "integer",
                "description": "Court Listener opinion ID.",
            },
        },
        "required": ["opinion_id"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_opinion(args: dict[str, Any]) -> dict[str, Any]:
    try:
        cl = _get_court_listener_client()
        result = await cl.get(f"/opinions/{args['opinion_id']}/")
        return _result(result)
    except Exception as exc:
        return _error(f"get_opinion failed: {exc}")


@tool(
    "query_opinion",
    "Ask a specific question about a legal opinion. Uses Mistral to find "
    "the answer grounded in the opinion text. More targeted than reading "
    "the raw opinion.",
    {
        "type": "object",
        "properties": {
            "opinion_id": {
                "type": "integer",
                "description": "Court Listener opinion ID from search_cases.",
            },
            "question": {
                "type": "string",
                "description": "Specific legal question to answer from the opinion.",
            },
        },
        "required": ["opinion_id", "question"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def query_opinion(args: dict[str, Any]) -> dict[str, Any]:
    try:
        mistral_key = os.getenv("MISTRAL_API_KEY")
        if not mistral_key:
            return _error("MISTRAL_API_KEY is not configured")

        cl = _get_court_listener_client()
        opinion = await cl.get(f"/opinions/{args['opinion_id']}/")

        raw = (
            opinion.get("xml_harvard")
            or opinion.get("html_lawbox")
            or opinion.get("html_with_citations")
            or opinion.get("plain_text")
            or ""
        )
        if not raw:
            return _error(f"No opinion text available for ID {args['opinion_id']}")

        clean = re.sub(r"<[^>]+>", " ", raw)
        clean = re.sub(r"\s+", " ", clean).strip()

        cluster_id = opinion.get("cluster_id", args["opinion_id"])
        case_name = f"Opinion {args['opinion_id']}"
        try:
            cluster = await cl.get(f"/clusters/{cluster_id}/")
            case_name = cluster.get("case_name", case_name)
        except Exception:
            pass

        system_prompt = (
            "You are a precise legal research assistant. "
            "Answer the question using ONLY the opinion text provided. "
            "Quote the relevant passage(s) directly. "
            "If the opinion does not address the question, say so explicitly."
        )
        user_prompt = f"OPINION: {case_name}\n\n{clean}\n\nQUESTION: {args['question']}"

        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {mistral_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "mistral-large-latest",
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()

        answer = data["choices"][0]["message"]["content"]
        return _result({
            "opinion_id": args["opinion_id"],
            "case_name": case_name,
            "question": args["question"],
            "answer": answer,
        })
    except Exception as exc:
        return _error(f"query_opinion failed: {exc}")


@tool(
    "query_document",
    "Ask a specific question about a document (PDF, DOCX, etc.) using "
    "Mistral's document Q&A. Provide either a file_path or a url. "
    "Use to verify facts without loading full text into context.",
    {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "Specific question to answer from the document.",
            },
            "file_path": {
                "type": "string",
                "description": "Absolute path to a local document file.",
            },
            "url": {
                "type": "string",
                "description": "Public URL to a document.",
            },
        },
        "required": ["question"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def query_document(args: dict[str, Any]) -> dict[str, Any]:
    try:
        mistral_key = os.getenv("MISTRAL_API_KEY")
        if not mistral_key:
            return _error("MISTRAL_API_KEY is not configured")
        file_path = args.get("file_path")
        url = args.get("url")
        if not file_path and not url:
            return _error("Provide either file_path or url")
        if file_path and url:
            return _error("Provide either file_path or url, not both")

        if file_path:
            path = Path(file_path).expanduser().resolve()
            if not path.exists():
                return _error(f"File not found: {file_path}")
            mime, _ = mimetypes.guess_type(str(path))
            mime = mime or "application/octet-stream"
            encoded = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
            document_url = f"data:{mime};base64,{encoded}"
            source = path.name
        else:
            document_url = url
            source = url

        async with httpx.AsyncClient(timeout=120) as http:
            resp = await http.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {mistral_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "mistral-large-latest",
                    "temperature": 0,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": args["question"]},
                                {"type": "document_url", "document_url": document_url},
                            ],
                        }
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return _result({
            "question": args["question"],
            "answer": data["choices"][0]["message"]["content"],
            "source": source,
        })
    except Exception as exc:
        return _error(f"query_document failed: {exc}")


@tool(
    "lookup_citation",
    "Look up a legal citation and return the matching case from Court "
    "Listener. Example citation: '384 U.S. 436'.",
    {
        "type": "object",
        "properties": {
            "citation": {
                "type": "string",
                "description": "Legal citation, e.g. '384 U.S. 436'.",
            },
        },
        "required": ["citation"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def lookup_citation(args: dict[str, Any]) -> dict[str, Any]:
    try:
        cl = _get_court_listener_client()
        raw = await cl.post("/citation-lookup/", data={"text": args["citation"]})
        result = raw if isinstance(raw, list) else [raw]
        return _result({"citations": result})
    except Exception as exc:
        return _error(f"lookup_citation failed: {exc}")


# ===================================================================
# LEGAL BRAIN TOOLS (Neo4j Knowledge Graph)
# ===================================================================

_kg = None
_kg_constraints_initialized = False


async def _get_kg():
    """Lazy-init the Neo4j Legal Brain client."""
    global _kg, _kg_constraints_initialized
    if _kg is None:
        from clients.legal_brain import Neo4jClient
        from config import config as war_room_config

        neo4j_cfg = war_room_config.neo4j
        if not neo4j_cfg.uri:
            raise RuntimeError(
                "NEO4J_URI not configured — add Neo4j credentials to .env"
            )
        _kg = Neo4jClient(neo4j_cfg.uri, neo4j_cfg.username, neo4j_cfg.password)
    if not _kg_constraints_initialized:
        await _kg.setup_constraints()
        _kg_constraints_initialized = True
    return _kg


# --- Write tools ---

@tool(
    "kg_ingest_case",
    "Ingest a case's intake data into the Legal Brain knowledge graph "
    "(Neo4j). Reads settings.json, documents_index.json, all metadata.json "
    "files, and case_summary.md. Creates Case, Document, Party, Statute, "
    "and CaseSummary nodes. Idempotent — safe to re-call.",
    {
        "type": "object",
        "properties": {
            "case_id": {
                "type": "string",
                "description": "Case workspace identifier.",
            },
            "case_root": {
                "type": "string",
                "description": "Absolute path to case root directory.",
            },
        },
        "required": ["case_id", "case_root"],
    },
)
async def kg_ingest_case(args: dict[str, Any]) -> dict[str, Any]:
    try:
        kg = await _get_kg()
        result = await kg.ingest_case(args["case_id"], args["case_root"])
        return _result(result)
    except Exception as exc:
        return _error(f"kg_ingest_case failed: {exc}")


@tool(
    "kg_ingest_strategy",
    "Ingest a strategy's CLAIMS.json and ATTACKS.json into the Legal Brain. "
    "Creates Claim, Attack, and Holding nodes with edges. Idempotent.",
    {
        "type": "object",
        "properties": {
            "case_id": {"type": "string", "description": "Case workspace identifier."},
            "claims_path": {
                "type": "string",
                "description": "Absolute path to CLAIMS.json.",
            },
            "attacks_path": {
                "type": "string",
                "description": "Absolute path to ATTACKS.json.",
            },
        },
        "required": ["case_id", "claims_path", "attacks_path"],
    },
)
async def kg_ingest_strategy(args: dict[str, Any]) -> dict[str, Any]:
    try:
        kg = await _get_kg()
        result = await kg.ingest_strategy(
            args["case_id"], args["claims_path"], args["attacks_path"]
        )
        return _result(result)
    except Exception as exc:
        return _error(f"kg_ingest_strategy failed: {exc}")


@tool(
    "kg_ingest_counter_requirements",
    "Ingest counter_requirements.json into the Legal Brain. Creates "
    "CounterRequirement and Fact nodes with REBUTTED_BY, SUPPORTED_BY, "
    "and SOURCED_FROM edges. Facts deduplicate by content hash.",
    {
        "type": "object",
        "properties": {
            "case_id": {"type": "string", "description": "Case workspace identifier."},
            "cr_path": {
                "type": "string",
                "description": "Absolute path to counter_requirements.json.",
            },
        },
        "required": ["case_id", "cr_path"],
    },
)
async def kg_ingest_counter_requirements(args: dict[str, Any]) -> dict[str, Any]:
    try:
        kg = await _get_kg()
        result = await kg.ingest_counter_requirements(args["case_id"], args["cr_path"])
        return _result(result)
    except Exception as exc:
        return _error(f"kg_ingest_counter_requirements failed: {exc}")


@tool(
    "kg_ingest_evidence_bundle",
    "Ingest evidence-bundle.json into the Legal Brain. Creates Exhibit "
    "nodes with HAS_EXHIBIT and MARKED_AS edges linking Documents to "
    "Exhibits.",
    {
        "type": "object",
        "properties": {
            "case_id": {"type": "string", "description": "Case workspace identifier."},
            "bundle_path": {
                "type": "string",
                "description": "Absolute path to evidence-bundle.json.",
            },
        },
        "required": ["case_id", "bundle_path"],
    },
)
async def kg_ingest_evidence_bundle(args: dict[str, Any]) -> dict[str, Any]:
    try:
        kg = await _get_kg()
        result = await kg.ingest_evidence_bundle(args["case_id"], args["bundle_path"])
        return _result(result)
    except Exception as exc:
        return _error(f"kg_ingest_evidence_bundle failed: {exc}")


# --- Read tools ---

@tool(
    "kg_get_case_documents",
    "Get all documents ingested for a case from the Legal Brain. Returns "
    "documents with types, processing status, and exhibit promotion status.",
    {
        "type": "object",
        "properties": {
            "case_id": {"type": "string", "description": "Case workspace identifier."},
            "document_type": {
                "type": "string",
                "description": 'Optional filter — "Motion", "Complaint", "Order", etc.',
            },
        },
        "required": ["case_id"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def kg_get_case_documents(args: dict[str, Any]) -> dict[str, Any]:
    try:
        kg = await _get_kg()
        result = await kg.get_case_documents(
            args["case_id"], args.get("document_type")
        )
        return _result(result)
    except Exception as exc:
        return _error(f"kg_get_case_documents failed: {exc}")


@tool(
    "kg_get_case_parties",
    "Get all parties in a case from the Legal Brain. Returns deduplicated "
    "parties with roles, representation info, and document mentions.",
    {
        "type": "object",
        "properties": {
            "case_id": {"type": "string", "description": "Case workspace identifier."},
        },
        "required": ["case_id"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def kg_get_case_parties(args: dict[str, Any]) -> dict[str, Any]:
    try:
        kg = await _get_kg()
        result = await kg.get_case_parties(args["case_id"])
        return _result(result)
    except Exception as exc:
        return _error(f"kg_get_case_parties failed: {exc}")


@tool(
    "kg_get_claim_support",
    "Get all facts and source documents supporting a specific claim. "
    "Traverses Claim ← Attack ← CounterRequirement ← Fact ← Document. "
    "Use before drafting to see your factual foundation.",
    {
        "type": "object",
        "properties": {
            "case_id": {"type": "string", "description": "Case workspace identifier."},
            "claim_id": {
                "type": "string",
                "description": 'Claim ID from CLAIMS.json, e.g. "003".',
            },
        },
        "required": ["case_id", "claim_id"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def kg_get_claim_support(args: dict[str, Any]) -> dict[str, Any]:
    try:
        kg = await _get_kg()
        result = await kg.get_claim_support(args["case_id"], args["claim_id"])
        return _result(result)
    except Exception as exc:
        return _error(f"kg_get_claim_support failed: {exc}")


@tool(
    "kg_get_attack_context",
    "Get full context for all attacks in a strategy from the Legal Brain. "
    "Returns threatened claims, adverse holdings, counter-requirements, "
    "and proof status. Use at the start of defensive strategy work.",
    {
        "type": "object",
        "properties": {
            "case_id": {"type": "string", "description": "Case workspace identifier."},
            "strategy_id": {
                "type": "string",
                "description": 'Strategy ID from ATTACKS.json, e.g. "009_monolithic_test".',
            },
        },
        "required": ["case_id", "strategy_id"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def kg_get_attack_context(args: dict[str, Any]) -> dict[str, Any]:
    try:
        kg = await _get_kg()
        result = await kg.get_attack_context(args["case_id"], args["strategy_id"])
        return _result(result)
    except Exception as exc:
        return _error(f"kg_get_attack_context failed: {exc}")


@tool(
    "kg_find_contradictions",
    "Search for facts that contradict or relate to a proposed assertion "
    "in the Legal Brain. Use before writing a new factual assertion to "
    "check for conflicts.",
    {
        "type": "object",
        "properties": {
            "case_id": {"type": "string", "description": "Case workspace identifier."},
            "assertion": {
                "type": "string",
                "description": "The fact assertion to check (plain text).",
            },
        },
        "required": ["case_id", "assertion"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def kg_find_contradictions(args: dict[str, Any]) -> dict[str, Any]:
    try:
        kg = await _get_kg()
        result = await kg.find_contradictions(args["case_id"], args["assertion"])
        return _result(result)
    except Exception as exc:
        return _error(f"kg_find_contradictions failed: {exc}")


@tool(
    "kg_get_exhibit_impact",
    "Get everything that depends on a specific exhibit in the Legal Brain. "
    "Traces Exhibit → Document → Facts → CRs → Attacks → Claims. "
    "Use when assessing the impact of a motion to exclude evidence.",
    {
        "type": "object",
        "properties": {
            "case_id": {"type": "string", "description": "Case workspace identifier."},
            "exhibit_label": {
                "type": "string",
                "description": 'Exhibit label, e.g. "Exhibit A", "Exhibit E".',
            },
        },
        "required": ["case_id", "exhibit_label"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def kg_get_exhibit_impact(args: dict[str, Any]) -> dict[str, Any]:
    try:
        kg = await _get_kg()
        result = await kg.get_exhibit_impact(args["case_id"], args["exhibit_label"])
        return _result(result)
    except Exception as exc:
        return _error(f"kg_get_exhibit_impact failed: {exc}")


@tool(
    "kg_get_unsupported_claims",
    "Find claims with weak or missing evidentiary support in the Legal "
    "Brain. Returns claims with no counter-requirements or no strong facts. "
    "Use for strategic gap analysis.",
    {
        "type": "object",
        "properties": {
            "case_id": {"type": "string", "description": "Case workspace identifier."},
        },
        "required": ["case_id"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def kg_get_unsupported_claims(args: dict[str, Any]) -> dict[str, Any]:
    try:
        kg = await _get_kg()
        result = await kg.get_unsupported_claims(args["case_id"])
        return _result(result)
    except Exception as exc:
        return _error(f"kg_get_unsupported_claims failed: {exc}")


@tool(
    "kg_get_case_readiness",
    "Get a per-claim readiness assessment for an entire case from the "
    "Legal Brain. Scores each claim as strong/moderate/weak/undefended. "
    "Use as the first tool when asked 'how strong is our case?'",
    {
        "type": "object",
        "properties": {
            "case_id": {"type": "string", "description": "Case workspace identifier."},
        },
        "required": ["case_id"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def kg_get_case_readiness(args: dict[str, Any]) -> dict[str, Any]:
    try:
        kg = await _get_kg()
        result = await kg.get_case_readiness(args["case_id"])
        return _result(result)
    except Exception as exc:
        return _error(f"kg_get_case_readiness failed: {exc}")


# ===================================================================
# STATUTES & REGULATIONS TOOLS
# ===================================================================

_ecfr_title_dates: dict[int, str] = {}


def _parse_cfr_citation(citation: str) -> tuple[int, str] | None:
    m = re.search(r"(\d+)\s*C\.?F\.?R\.?\s*[§\s]*(\d+[\.\d]*)", citation, re.IGNORECASE)
    if m:
        return int(m.group(1)), m.group(2)
    return None


def _parse_usc_citation(citation: str) -> tuple[int, str] | None:
    m = re.search(r"(\d+)\s*U\.?S\.?C\.?\s*[§\s]*(\d+[a-z\-\d]*)", citation, re.IGNORECASE)
    if m:
        return int(m.group(1)), m.group(2)
    return None


def _strip_xml_tags(xml: str) -> str:
    text = re.sub(r"<[^>]+>", " ", xml)
    return re.sub(r"\s+", " ", text).strip()


async def _ecfr_latest_date(client: httpx.AsyncClient, title_num: int) -> str:
    if title_num not in _ecfr_title_dates:
        resp = await client.get("https://www.ecfr.gov/api/versioner/v1/titles.json", timeout=10.0)
        resp.raise_for_status()
        for t in resp.json().get("titles", []):
            _ecfr_title_dates[t["number"]] = t["latest_issue_date"]
    return _ecfr_title_dates.get(title_num, "")


@tool(
    "lookup_cfr_section",
    "Fetch the full text of a Code of Federal Regulations (CFR) section "
    "from eCFR. Returns authoritative regulatory text directly. "
    "Accepts: '29 CFR 1630.2', '12 CFR § 226.4', '47 CFR 73.3526'.",
    {
        "type": "object",
        "properties": {
            "citation": {"type": "string", "description": "CFR citation string."},
        },
        "required": ["citation"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def lookup_cfr_section(args: dict[str, Any]) -> dict[str, Any]:
    try:
        parsed = _parse_cfr_citation(args["citation"])
        if not parsed:
            return _error(f"Could not parse CFR citation: {args['citation']!r}")
        title_num, section = parsed

        async with httpx.AsyncClient(timeout=20.0) as client:
            issue_date = await _ecfr_latest_date(client, title_num)
            if not issue_date:
                return _error(f"CFR Title {title_num} not found in eCFR.")
            url = f"https://www.ecfr.gov/api/versioner/v1/full/{issue_date}/title-{title_num}.xml?section={section}"
            resp = await client.get(url)
            resp.raise_for_status()

        xml = resp.text
        heading_m = re.search(r"<HEAD>([^<]+)</HEAD>", xml)
        heading = heading_m.group(1).strip() if heading_m else ""
        text = _strip_xml_tags(xml)

        return _result({
            "citation": f"{title_num} CFR § {section}",
            "title": title_num,
            "section": section,
            "heading": heading,
            "text": text,
            "as_of": issue_date,
            "source": "eCFR (ecfr.gov)",
        })
    except httpx.HTTPStatusError as e:
        return _error(f"eCFR HTTP {e.response.status_code}: {e.response.text[:200]}")
    except Exception as exc:
        return _error(f"lookup_cfr_section failed: {exc}")


@tool(
    "search_cfr",
    "Full-text search of the Code of Federal Regulations via eCFR. "
    "Use when you have a regulatory concept but don't know the exact "
    "section. Follow up with lookup_cfr_section for full text.",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search terms."},
            "title": {"type": "integer", "description": "Optional CFR title number to restrict search."},
            "max_results": {"type": "integer", "description": "Max results. Default: 5."},
        },
        "required": ["query"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def search_cfr(args: dict[str, Any]) -> dict[str, Any]:
    try:
        max_results = min(args.get("max_results", 5), 20)
        search_query = f"{args['title']} CFR {args['query']}" if args.get("title") else args["query"]
        params: dict = {"query": search_query, "per_page": max_results}

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get("https://www.ecfr.gov/api/search/v1/results", params=params)
            resp.raise_for_status()

        data = resp.json()
        results = []
        for r in data.get("results", []):
            h = r.get("hierarchy", {})
            hh = r.get("hierarchy_headings", {})
            section = h.get("section", "")
            citation = f"{h.get('title', '')} CFR § {section}" if section else f"Title {h.get('title', '')} CFR"
            results.append({
                "citation": citation,
                "heading": hh.get("section", "") or hh.get("part", ""),
                "excerpt": _strip_xml_tags(r.get("full_text_excerpt", "")),
                "hierarchy": {
                    "title": hh.get("title", ""),
                    "chapter": hh.get("chapter", ""),
                    "part": hh.get("part", ""),
                    "section": hh.get("section", ""),
                },
            })

        return _result({"query": args["query"], "count": len(results), "results": results})
    except Exception as exc:
        return _error(f"search_cfr failed: {exc}")


@tool(
    "lookup_usc_section",
    "Fetch the full text of a United States Code (USC) section from "
    "uscode.house.gov. Returns authoritative statutory text. "
    "Accepts: '42 U.S.C. 12112', '42 USC § 1983', '15 U.S.C. 1681'.",
    {
        "type": "object",
        "properties": {
            "citation": {"type": "string", "description": "USC citation string."},
        },
        "required": ["citation"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def lookup_usc_section(args: dict[str, Any]) -> dict[str, Any]:
    try:
        parsed = _parse_usc_citation(args["citation"])
        if not parsed:
            return _error(f"Could not parse USC citation: {args['citation']!r}")
        title_num, section = parsed
        view_url = (
            f"https://uscode.house.gov/view.xhtml"
            f"?req=granuleid:USC-prelim-title{title_num}-section{section}&edition=prelim"
        )

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(view_url)
            resp.raise_for_status()

        html = resp.text
        heading_m = re.search(r'<h3[^>]*class="[^"]*section-head[^"]*"[^>]*>([^<]+)</h3>', html, re.IGNORECASE)
        heading = heading_m.group(1).strip() if heading_m else ""

        body_m = re.findall(r'<p[^>]*class="[^"]*statutory-body[^"]*"[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
        if body_m:
            text = " ".join(_strip_xml_tags(p) for p in body_m)
        else:
            content_m = re.search(r'<div[^>]*id="[^"]*content[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
            text = _strip_xml_tags(content_m.group(1)) if content_m else _strip_xml_tags(html[:5000])

        if not text.strip():
            return _error(f"Section {args['citation']} was found but content could not be extracted.")

        return _result({
            "citation": f"{title_num} U.S.C. § {section}",
            "title": title_num,
            "section": section,
            "heading": heading,
            "text": text[:8000],
            "source": "uscode.house.gov (OLRC)",
            "url": view_url,
        })
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (404, 406):
            return _error(f"Section {args['citation']} not found.")
        return _error(f"HTTP {e.response.status_code} fetching USC section")
    except Exception as exc:
        return _error(f"lookup_usc_section failed: {exc}")


# ===================================================================
# STEALTH SCRAPER TOOL
# ===================================================================

@tool(
    "fetch_protected_url",
    "Fetch a URL through a remote stealth browser (CloakBrowser). "
    "Use when a legal site blocks normal HTTP clients with Cloudflare "
    "or similar anti-bot protection. For plain public endpoints, prefer "
    "the dedicated tools (CourtListener, eCFR, uscode) — they are "
    "faster and authoritative.",
    {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Absolute https:// URL to fetch."},
            "wait_for": {
                "type": "string",
                "enum": ["domcontentloaded", "load"],
                "description": "Page load signal. Default: domcontentloaded.",
            },
            "timeout_ms": {"type": "integer", "description": "Hard timeout in ms."},
            "return_format": {
                "type": "string",
                "enum": ["html", "text"],
                "description": "html = full rendered HTML, text = cheap extraction. Default: html.",
            },
        },
        "required": ["url"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def fetch_protected_url(args: dict[str, Any]) -> dict[str, Any]:
    try:
        from clients import ScraperClient, ScraperError
        from config import config as war_room_config

        client = ScraperClient(war_room_config.scraper)
        result = await client.fetch(
            url=args["url"],
            wait_for=args.get("wait_for", "domcontentloaded"),
            timeout_ms=args.get("timeout_ms"),
            return_format=args.get("return_format", "html"),
        )
        return _result({
            "url": result.url,
            "final_url": result.final_url,
            "status": result.status,
            "title": result.title,
            "content": result.content,
            "content_bytes": result.content_bytes,
            "elapsed_ms": result.elapsed_ms,
            "fetched_at": result.fetched_at,
        })
    except Exception as exc:
        msg = str(exc)
        code = "DOMAIN_NOT_ALLOWED" if "DOMAIN_NOT_ALLOWED" in msg else (
            "TIMEOUT" if "TIMEOUT" in msg else "SCRAPER_ERROR"
        )
        return {"content": [{"type": "text", "text": msg}], "is_error": True}


# ===================================================================
# Server factory
# ===================================================================

def create_external_tools_server() -> Any:
    """Return an in-process SDK MCP server with all external integration tools.

    Usage in manager.py:
        legal_hub = create_external_tools_server()
        options = ClaudeAgentOptions(
            mcp_servers={"vision": vision_server, "legal_hub": legal_hub},
            allowed_tools=["mcp__vision__*", "mcp__legal_hub__*", ...],
        )
    """
    return create_sdk_mcp_server(
        name="legal_hub",
        version="1.0.0",
        tools=[
            # Research
            deep_research,
            quick_search,
            extract_page,
            write_report,
            # Court Listener
            search_cases,
            get_opinion,
            query_opinion,
            query_document,
            lookup_citation,
            # Statutes & Regulations
            lookup_cfr_section,
            search_cfr,
            lookup_usc_section,
            # Stealth Scraper
            fetch_protected_url,
            # Legal Brain (Neo4j) — disabled pending infrastructure setup
            # kg_ingest_case,
            # kg_ingest_strategy,
            # kg_ingest_counter_requirements,
            # kg_ingest_evidence_bundle,
            # kg_get_case_documents,
            # kg_get_case_parties,
            # kg_get_claim_support,
            # kg_get_attack_context,
            # kg_find_contradictions,
            # kg_get_exhibit_impact,
            # kg_get_unsupported_claims,
            # kg_get_case_readiness,
        ],
    )
