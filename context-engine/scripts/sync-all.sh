#!/bin/bash

# Universal Context Engineering Framework
# Universal Sync Script - Converts context to all supported AI tool formats

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_CONTX_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$PROJECT_CONTX_DIR/.." && pwd)"

# Define the context-engine directory at the project root (outside contx)
CONTEXT_ENGINE_DIR="$PROJECT_ROOT/context-engine"

# Helper function: copy directory if source exists
copy_dir_if_exists() {
    local src="$1"
    local dest="$2"
    mkdir -p "$dest"
    if [ -d "$src" ]; then
        cp -r "$src/." "$dest/"
    fi
}

# Helper function: copy file if source exists
copy_file_if_exists() {
    local src="$1"
    local dest="$2"
    local dest_dir
    dest_dir="$(dirname "$dest")"
    mkdir -p "$dest_dir"
    if [ -f "$src" ]; then
        cp "$src" "$dest"
    fi
}

# Create destination directory structure
mkdir -p "$CONTEXT_ENGINE_DIR/domain-contexts"
mkdir -p "$CONTEXT_ENGINE_DIR/templates/specs"
mkdir -p "$CONTEXT_ENGINE_DIR/tasks"
mkdir -p "$CONTEXT_ENGINE_DIR/standards"
mkdir -p "$CONTEXT_ENGINE_DIR/specs"
mkdir -p "$CONTEXT_ENGINE_DIR/scripts"
mkdir -p "$CONTEXT_ENGINE_DIR/guides"

# Ensure source directories exist in contx (create if missing)
mkdir -p "$PROJECT_CONTX_DIR/context-engine/domain-contexts"
mkdir -p "$PROJECT_CONTX_DIR/templates"
mkdir -p "$PROJECT_CONTX_DIR/standards"
mkdir -p "$PROJECT_CONTX_DIR/scripts"
mkdir -p "$PROJECT_CONTX_DIR/guides"

# Copy context-engine contents to project root context-engine
copy_file_if_exists "$PROJECT_CONTX_DIR/global-context.md" "$CONTEXT_ENGINE_DIR/global-context.md"
copy_dir_if_exists "$PROJECT_CONTX_DIR/context-engine/domain-contexts" "$CONTEXT_ENGINE_DIR/domain-contexts"
copy_dir_if_exists "$PROJECT_CONTX_DIR/templates" "$CONTEXT_ENGINE_DIR/templates"
copy_dir_if_exists "$PROJECT_CONTX_DIR/standards" "$CONTEXT_ENGINE_DIR/standards"
copy_dir_if_exists "$PROJECT_CONTX_DIR/scripts" "$CONTEXT_ENGINE_DIR/scripts"
copy_dir_if_exists "$PROJECT_CONTX_DIR/guides" "$CONTEXT_ENGINE_DIR/guides"

# Agent files (static): copy authored files from contx into project root
mkdir -p "$PROJECT_ROOT/.augment"
if [ -d "$PROJECT_CONTX_DIR/.augment/rules" ]; then
    cp -R "$PROJECT_CONTX_DIR/.augment/rules" "$PROJECT_ROOT/.augment/"
fi

# Copy AGENTS.md to project root (and generate WARP.md, GEMINI.md)
if [ -f "$PROJECT_CONTX_DIR/AGENTS.md" ]; then
    cp "$PROJECT_CONTX_DIR/AGENTS.md" "$PROJECT_ROOT/AGENTS.md"
    cp "$PROJECT_ROOT/AGENTS.md" "$PROJECT_ROOT/WARP.md"
    cp "$PROJECT_ROOT/AGENTS.md" "$PROJECT_ROOT/GEMINI.md"
fi

echo "Context synchronized successfully!"
