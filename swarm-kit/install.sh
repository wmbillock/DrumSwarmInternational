#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║  DCI Swarm — Installer                                         ║
# ║  Registers skills, agents, and plugins for Claude Code          ║
# ╚══════════════════════════════════════════════════════════════════╝
#
# Usage: ./swarm-kit/install.sh [--symlink | --copy] [--skip-plugins] [--skip-llm-check]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CLAUDE_DIR="${HOME}/.claude"
SKILLS_DIR="${CLAUDE_DIR}/skills"
AGENTS_DIR="${CLAUDE_DIR}/agents"

# Defaults
MODE="symlink"
SKIP_PLUGINS=false
SKIP_LLM=false

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --symlink)  MODE="symlink"; shift ;;
        --copy)     MODE="copy"; shift ;;
        --skip-plugins) SKIP_PLUGINS=true; shift ;;
        --skip-llm-check) SKIP_LLM=true; shift ;;
        -h|--help)
            echo "Usage: ./swarm-kit/install.sh [--symlink | --copy] [--skip-plugins] [--skip-llm-check]"
            echo ""
            echo "  --symlink       (default) Symlink skills/agents so project stays source of truth"
            echo "  --copy          Copy files instead of symlinking"
            echo "  --skip-plugins  Skip plugin installation"
            echo "  --skip-llm-check  Skip LLM provider detection"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[install]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[install]${NC} $1"; }
log_error() { echo -e "${RED}[install]${NC} $1"; }

echo ""
echo -e "${BOLD}  DCI Swarm — Install${NC}"
echo -e "${DIM}  Mode: $MODE${NC}"
echo ""

# --- Step 1: LLM Detection ---
if [ "$SKIP_LLM" = false ]; then
    log_info "Detecting LLM providers..."
    bash "$SCRIPT_DIR/detect-llm.sh"
    echo ""
fi

# --- Step 2: Install Skills ---
log_info "Installing skills ($MODE)..."
mkdir -p "$SKILLS_DIR"

for skill_dir in "$SCRIPT_DIR"/skills/*/; do
    skill_name="$(basename "$skill_dir")"
    target_dir="$SKILLS_DIR/$skill_name"

    if [ "$MODE" = "symlink" ]; then
        # Remove existing (file, dir, or symlink) and replace with symlink
        rm -rf "$target_dir"
        ln -s "$skill_dir" "$target_dir"
        log_info "  $skill_name -> ${skill_dir#$PROJECT_ROOT/}"
    else
        rm -rf "$target_dir"
        cp -r "$skill_dir" "$target_dir"
        log_info "  $skill_name (copied)"
    fi
done

# --- Step 3: Install Agents ---
log_info "Installing agents ($MODE)..."
mkdir -p "$AGENTS_DIR"

for agent_file in "$SCRIPT_DIR"/agents/*.md; do
    agent_name="$(basename "$agent_file")"
    target_file="$AGENTS_DIR/$agent_name"

    if [ "$MODE" = "symlink" ]; then
        rm -f "$target_file"
        ln -s "$agent_file" "$target_file"
        log_info "  $agent_name -> ${agent_file#$PROJECT_ROOT/}"
    else
        cp "$agent_file" "$target_file"
        log_info "  $agent_name (copied)"
    fi
done

# --- Step 4: Install Plugins ---
if [ "$SKIP_PLUGINS" = false ]; then
    log_info "Installing plugins..."

    if ! command -v claude &>/dev/null; then
        log_warn "Claude CLI not found — skipping plugin installation"
        log_warn "Install Claude CLI first, then re-run: ./dci install"
    else
        # Parse plugins.yaml and install required plugins
        # Simple YAML parsing — reads name fields under required: section
        in_required=false
        in_recommended=false
        while IFS= read -r line; do
            case "$line" in
                "required:") in_required=true; in_recommended=false ;;
                "recommended:") in_required=false; in_recommended=true ;;
            esac

            if [[ "$line" =~ ^[[:space:]]*-[[:space:]]*name:[[:space:]]*(.+)$ ]]; then
                plugin_name="${BASH_REMATCH[1]}"
                if [ "$in_required" = true ]; then
                    log_info "  Installing required plugin: $plugin_name"
                    claude plugin install "$plugin_name" 2>/dev/null || log_warn "  Failed to install $plugin_name (may already be installed)"
                elif [ "$in_recommended" = true ]; then
                    log_info "  Installing recommended plugin: $plugin_name"
                    claude plugin install "$plugin_name" 2>/dev/null || log_warn "  Failed to install $plugin_name (may already be installed)"
                fi
            fi
        done < "$SCRIPT_DIR/plugins.yaml"
    fi
fi

# --- Step 5: Summary ---
echo ""
echo -e "${BOLD}  Installation Complete${NC}"
echo ""
log_info "Skills installed:"
for skill_dir in "$SCRIPT_DIR"/skills/*/; do
    skill_name="$(basename "$skill_dir")"
    if [ -L "$SKILLS_DIR/$skill_name" ]; then
        echo -e "    ${GREEN}$skill_name${NC} (symlinked)"
    elif [ -d "$SKILLS_DIR/$skill_name" ]; then
        echo -e "    ${GREEN}$skill_name${NC} (copied)"
    else
        echo -e "    ${RED}$skill_name${NC} (FAILED)"
    fi
done

log_info "Agents installed:"
for agent_file in "$SCRIPT_DIR"/agents/*.md; do
    agent_name="$(basename "$agent_file")"
    if [ -L "$AGENTS_DIR/$agent_name" ]; then
        echo -e "    ${GREEN}$agent_name${NC} (symlinked)"
    elif [ -f "$AGENTS_DIR/$agent_name" ]; then
        echo -e "    ${GREEN}$agent_name${NC} (copied)"
    else
        echo -e "    ${RED}$agent_name${NC} (FAILED)"
    fi
done

echo ""
log_info "Run ${BOLD}./dci ten-hut${NC} to start the swarm."
echo ""
