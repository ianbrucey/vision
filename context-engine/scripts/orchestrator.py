#!/usr/bin/env python3
"""
Zero Ambiguity Council Orchestrator

The "Relay Race" automation that takes the output of one agent phase
and forces it to become the input for the next phase.

This ensures no context is dropped and no steps are skipped.

Usage:
    python scripts/orchestrator.py

Prerequisites:
    - A 00-Brief.md file must exist in context-engine/specs/
    - Replace run_agent_command() with your actual CLI tool calls

See guides/council-workflow.md for detailed explanation.
"""

import os
import subprocess
import sys
import json

# --- CONFIGURATION ---
# Paths relative to project root (run from project root)
DIRS = {
    "SPECS": "context-engine/specs",
    "TEMPLATES": "context-engine/templates/specs",
    "STANDARDS": "context-engine/standards",
    "DOMAIN_CONTEXTS": "context-engine/domain-contexts"
}

FILES = {
    "BRIEF": os.path.join(DIRS["SPECS"], "00-Brief.md"),
    "INFRA": os.path.join(DIRS["SPECS"], "00.5-existing-infrastructure.md"),
    "SCHEMA": os.path.join(DIRS["SPECS"], "01-schema.sql"),
    "API": os.path.join(DIRS["SPECS"], "02-api-contract.json"),
    "FIXTURES": os.path.join(DIRS["SPECS"], "03-fixtures.json"),
    "UI": os.path.join(DIRS["SPECS"], "04-ui-specs.md"),
    "PLAN": os.path.join(DIRS["SPECS"], "05-implementation-plan.md"),
}

# Directories to scan for existing infrastructure
SCAN_DIRS = {
    "models": ["app/Models", "src/models", "models"],
    "migrations": ["database/migrations", "migrations", "alembic/versions"],
    "controllers": ["app/Http/Controllers", "src/controllers", "controllers", "app/controllers"],
    "routes": ["routes", "src/routes"],
    "components": ["resources/views/components", "src/components", "components"],
}


def ensure_dirs():
    """Create the artifact directories if they don't exist."""
    for d in DIRS.values():
        os.makedirs(d, exist_ok=True)


def scan_existing_infrastructure():
    """
    Scan the project for existing code that might be relevant.

    Returns:
        A string containing relevant existing code snippets, or empty string if none found.
    """
    found_files = []

    for category, paths in SCAN_DIRS.items():
        for path in paths:
            if os.path.exists(path):
                print(f"   🔍 Scanning {path}...")
                for root, dirs, files in os.walk(path):
                    for file in files:
                        # Skip non-code files
                        if not file.endswith(('.php', '.py', '.ts', '.js', '.sql', '.json', '.vue', '.jsx', '.tsx')):
                            continue

                        filepath = os.path.join(root, file)
                        try:
                            with open(filepath, 'r') as f:
                                content = f.read()

                            # Only include files under 500 lines to avoid context overflow
                            if content.count('\n') < 500:
                                found_files.append(f"\n### {filepath}\n```\n{content}\n```\n")
                        except Exception as e:
                            print(f"   ⚠️  Could not read {filepath}: {e}")
                break  # Only use first matching path per category

    if not found_files:
        return ""

    # Limit total context to prevent token overflow
    combined = "".join(found_files)
    if len(combined) > 100000:  # ~25k tokens
        print("   ⚠️  Truncating infrastructure scan (too much code)")
        combined = combined[:100000] + "\n\n[TRUNCATED - Too much code to include]"

    return combined


def read_file(filepath):
    """Read a file if it exists, otherwise return None."""
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return f.read()
    return None


def load_domain_contexts(brief_content):
    """
    Load relevant domain context files based on keywords in the Brief.

    Domain contexts contain:
    1. Business intent - WHY things work the way they do
    2. Code navigation - WHERE to find things, HOW to trace through the code

    Args:
        brief_content: The Brief content to scan for domain keywords

    Returns:
        Concatenated domain context content, or empty string if none found.
    """
    domain_contexts_dir = DIRS["DOMAIN_CONTEXTS"]

    if not os.path.exists(domain_contexts_dir):
        print("   📂 No domain-contexts directory found")
        return ""

    # Get all domain context files
    context_files = []
    for file in os.listdir(domain_contexts_dir):
        if file.endswith('.md'):
            filepath = os.path.join(domain_contexts_dir, file)
            context_files.append((file, filepath))

    if not context_files:
        print("   📂 No domain context files found")
        return ""

    print(f"   📚 Found {len(context_files)} domain context files")

    # Load all domain contexts (they're curated knowledge, should be included)
    # In a more sophisticated version, we could filter based on Brief keywords
    loaded_contexts = []
    for filename, filepath in context_files:
        try:
            with open(filepath, 'r') as f:
                content = f.read()

            # Skip template files or empty files
            if "[Date]" in content and "[Domain Name]" in content:
                print(f"      ⏭️  Skipping template: {filename}")
                continue

            loaded_contexts.append(f"\n### Domain Context: {filename}\n{content}\n")
            print(f"      ✅ Loaded: {filename}")
        except Exception as e:
            print(f"      ⚠️  Could not read {filename}: {e}")

    if not loaded_contexts:
        return ""

    combined = "".join(loaded_contexts)

    # Limit to prevent token overflow
    if len(combined) > 50000:  # ~12k tokens
        print("   ⚠️  Truncating domain contexts (too large)")
        combined = combined[:50000] + "\n\n[TRUNCATED - Domain contexts too large]"

    return combined


def save_file(filepath, content):
    """Save the artifact to disk."""
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"  💾 Saved artifact: {filepath}")


def run_agent_command(agent_name, system_role, prompt, context_content):
    """
    The Relay Mechanism.

    Calls the appropriate AI CLI tool based on agent_name.

    Args:
        agent_name: Which agent to use ("Auggie" or "Gemini")
        system_role: The persona for this phase
        prompt: The task instruction
        context_content: All context files concatenated

    Returns:
        The agent's output string
    """
    print(f"\n🤖 Waking up {agent_name} ({system_role})...")

    full_prompt = f"""
ROLE: {system_role}

CONTEXT FILES:
{context_content}

TASK:
{prompt}
"""

    try:
        if agent_name == "Auggie":
            # Call Augment CLI (assuming 'auggie' command exists)
            print(f"   ...calling auggie CLI...")
            process = subprocess.run(
                ["auggie", "-p", full_prompt],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if process.returncode != 0:
                print(f"   ⚠️  auggie returned error code {process.returncode}")
                print(f"   stderr: {process.stderr}")
                sys.exit(1)

            return process.stdout.strip()

        elif agent_name == "Gemini":
            # Call Gemini CLI (assuming 'gemini' command exists)
            print(f"   ...calling gemini CLI...")
            process = subprocess.run(
                ["gemini", "-p", full_prompt],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if process.returncode != 0:
                print(f"   ⚠️  gemini returned error code {process.returncode}")
                print(f"   stderr: {process.stderr}")
                sys.exit(1)

            return process.stdout.strip()

        else:
            print(f"   ❌ Unknown agent: {agent_name}")
            sys.exit(1)

    except FileNotFoundError as e:
        print(f"\n   ❌ CLI tool not found: {e.filename}")
        print(f"   Make sure '{e.filename}' is installed and in your PATH")
        print(f"\n   Installation hints:")
        if "auggie" in str(e.filename):
            print(f"   - Augment CLI: Check Augment documentation")
        if "gemini" in str(e.filename):
            print(f"   - Gemini CLI: pip install google-generativeai")
        sys.exit(1)

    except subprocess.TimeoutExpired:
        print(f"\n   ❌ {agent_name} timed out after 5 minutes")
        sys.exit(1)


def main():
    print("=" * 60)
    print("🏛️  THE COUNCIL IS NOW IN SESSION")
    print("=" * 60)
    
    ensure_dirs()

    # --- PHASE 0: CHECK PRE-REQUISITES ---
    brief_content = read_file(FILES["BRIEF"])

    if not brief_content:
        print(f"\n❌ STOP: No Strategic Brief found at {FILES['BRIEF']}")
        print("   The Brief must be approved before the Council can convene.")
        print(f"\n   To start, copy the template:")
        print(f"   cp {DIRS['TEMPLATES']}/00-Brief.md {FILES['BRIEF']}")
        sys.exit(1)

    print("\n✅ Strategic Brief found.")

    # --- LOAD DOMAIN CONTEXTS ---
    print("\n📚 Loading Domain Contexts...")
    domain_contexts = load_domain_contexts(brief_content)
    if domain_contexts:
        print(f"   ✅ Domain contexts loaded ({len(domain_contexts)} chars)")
    else:
        print("   ℹ️  No applicable domain contexts found")

    # --- PHASE 0: ARCHAEOLOGY (Infrastructure Discovery) ---
    print("\n" + "-" * 60)
    print("PHASE 0: THE ARCHAEOLOGIST (Infrastructure Discovery)")
    print("-" * 60)

    if not os.path.exists(FILES["INFRA"]):
        # Scan for existing code files
        existing_code = scan_existing_infrastructure()

        if existing_code:
            print(f"\n   📁 Found existing code in {len(existing_code)} locations")

            # Build context with domain contexts if available
            archaeology_context = f"--- BRIEF ---\n{brief_content}\n\n--- EXISTING CODE ---\n{existing_code}"
            if domain_contexts:
                archaeology_context = f"--- DOMAIN CONTEXTS (Business Intent + Code Navigation) ---\n{domain_contexts}\n\n{archaeology_context}"

            infra_analysis = run_agent_command(
                agent_name="Auggie",
                system_role="Infrastructure Archaeologist",
                prompt="""Analyze the existing infrastructure and the Brief.

IMPORTANT: If Domain Contexts are provided, use them to understand:
1. Business rules and intent (WHY things work the way they do)
2. Code navigation (WHERE to find related files and HOW they connect)

Your task:
1. Identify which existing tables/models are relevant to this feature
2. Identify which existing API endpoints can be reused
3. Identify what is NET NEW (must be created)
4. Flag potential conflicts or constraints

Output a structured analysis following this format:

## Existing Infrastructure to REUSE
[List tables, endpoints, models that already exist and should NOT be recreated]

## Existing Infrastructure to EXTEND
[List what needs modification - e.g., "Add 'status' column to events table"]

## Net New Infrastructure
[List what must be created from scratch]

## Constraints & Warnings
[List any conflicts, dependencies, or things to avoid]

Be specific. Reference actual table names, column names, and file paths from the existing code.""",
                context_content=archaeology_context
            )
            save_file(FILES["INFRA"], infra_analysis)
        else:
            print("   ℹ️  No existing infrastructure found. This appears to be a greenfield project.")
            # Create a minimal infra file indicating greenfield
            save_file(FILES["INFRA"], "# Existing Infrastructure Analysis\n\n**Status:** Greenfield project - no existing infrastructure detected.\n\nAll specs will be net-new.")
    else:
        print("  ⏩ Infrastructure analysis already exists. Skipping.")

    # Load infrastructure for subsequent phases
    infra_content = read_file(FILES["INFRA"])

    # --- PHASE A: DATA ARCHITECTURE (Auggie) ---
    print("\n" + "-" * 60)
    print("PHASE A: THE VAULT MASTER (Database Schema)")
    print("-" * 60)

    # Build base context for all phases
    base_context = f"--- BRIEF ---\n{brief_content}\n\n--- EXISTING INFRASTRUCTURE ---\n{infra_content}"
    if domain_contexts:
        base_context = f"--- DOMAIN CONTEXTS (Business Intent + Code Navigation) ---\n{domain_contexts}\n\n{base_context}"

    if not os.path.exists(FILES["SCHEMA"]):
        schema_sql = run_agent_command(
            agent_name="Auggie",
            system_role="Database Architect",
            prompt="""Read the Brief, Domain Contexts, and Existing Infrastructure Analysis.

Use Domain Contexts to understand:
- Business rules (e.g., "Events cannot be cancelled within 2 hours")
- Existing schema patterns and naming conventions
- Relationships between entities

CRITICAL RULES:
1. Do NOT recreate tables that already exist (see Infrastructure Analysis)
2. For existing tables that need changes, output ALTER TABLE statements
3. For net-new tables, output CREATE TABLE statements
4. Follow naming conventions from existing code

Output ONLY valid SQL. No markdown, no explanations.""",
            context_content=base_context
        )
        save_file(FILES["SCHEMA"], schema_sql)
    else:
        print("  ⏩ Schema already exists. Skipping.")

    # --- PHASE B: API ARCHITECTURE (Auggie) ---
    print("\n" + "-" * 60)
    print("PHASE B: THE GATEKEEPER (API Contract)")
    print("-" * 60)

    if not os.path.exists(FILES["API"]):
        schema_content = read_file(FILES["SCHEMA"])
        api_json = run_agent_command(
            agent_name="Auggie",
            system_role="API Architect",
            prompt="""Read the Brief, Domain Contexts, Infrastructure Analysis, and Schema.

Use Domain Contexts to understand:
- Existing endpoint patterns and conventions
- Authentication/authorization requirements
- Business logic that affects API design

CRITICAL RULES:
1. Do NOT define endpoints that already exist (see Infrastructure Analysis)
2. Mark existing endpoints as "existing: true" in the contract
3. Only define NET NEW endpoints in detail
4. All fields must come from the Schema
5. Follow naming and structure conventions from existing API

Output ONLY valid JSON.""",
            context_content=f"{base_context}\n\n--- SCHEMA ---\n{schema_content}"
        )
        save_file(FILES["API"], api_json)
    else:
        print("  ⏩ API Contract already exists. Skipping.")

    # --- PHASE C: EVIDENCE GENERATION (Gemini) ---
    print("\n" + "-" * 60)
    print("PHASE C: THE WITNESS (Data Fixtures)")
    print("-" * 60)
    
    if not os.path.exists(FILES["FIXTURES"]):
        api_content = read_file(FILES["API"])
        fixtures_json = run_agent_command(
            agent_name="Gemini",
            system_role="Data Specialist",
            prompt="Read the API Contract. Generate realistic mock data (JSON) for every endpoint. Include edge cases. Output ONLY valid JSON.",
            context_content=f"--- API CONTRACT ---\n{api_content}"
        )
        save_file(FILES["FIXTURES"], fixtures_json)
    else:
        print("  ⏩ Fixtures already exist. Skipping.")

    # --- PHASE D: IMPLEMENTATION PLANNING (Auggie) ---
    print("\n" + "-" * 60)
    print("PHASE D: THE FOREMAN (Implementation Plan)")
    print("-" * 60)

    if not os.path.exists(FILES["PLAN"]):
        schema_content = read_file(FILES["SCHEMA"])
        api_content = read_file(FILES["API"])
        fixtures_content = read_file(FILES["FIXTURES"])

        plan_md = run_agent_command(
            agent_name="Auggie",
            system_role="Project Manager",
            prompt="""Read all Specs and Infrastructure Analysis. Create atomic tickets.

CRITICAL RULES:
1. Tickets for EXISTING infrastructure = "Modify" or "Extend" (not "Create")
2. Tickets for NET NEW infrastructure = "Create"
3. Sequence: DB → API → UI
4. Each ticket must reference a specific spec file
5. Mark which tickets touch existing code vs. new code

Output a structured implementation plan.""",
            context_content=f"""
--- BRIEF ---
{brief_content}

--- EXISTING INFRASTRUCTURE ---
{infra_content}

--- SCHEMA ---
{schema_content}

--- API CONTRACT ---
{api_content}

--- FIXTURES ---
{fixtures_content}
"""
        )
        save_file(FILES["PLAN"], plan_md)
    else:
        print("  ⏩ Plan already exists. Skipping.")

    print("\n" + "=" * 60)
    print("✅ COUNCIL SESSION ADJOURNED")
    print("=" * 60)
    print(f"\nArtifacts generated in: {DIRS['SPECS']}/")
    print("\nReady for Execution Phase (State 4).")
    print("To execute the plan with sub-agents:")
    print("  python scripts/executor.py --list     # Preview tickets")
    print("  python scripts/executor.py            # Execute all tickets")
    print("  python scripts/executor.py --ticket 1 # Execute specific ticket\n")


if __name__ == "__main__":
    main()

