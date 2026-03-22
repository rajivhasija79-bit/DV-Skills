#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# run_chipagent_workspace.bash
# DV Skills GUI — Workspace section
#
# Environment variables injected by the GUI backend:
#   WORKSPACE_DIR   PROJECT_NAME   SPEC_PATH
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

WORKSPACE_DIR="${WORKSPACE_DIR:-}"
PROJECT_NAME="${PROJECT_NAME:-project}"
SPEC_PATH="${SPEC_PATH:-}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ChipAgent — Workspace Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Workspace : ${WORKSPACE_DIR:-(not set)}"
echo "  Spec path : ${SPEC_PATH:-(not set)}"
echo ""

if [[ -z "$WORKSPACE_DIR" ]]; then
  echo "ERROR: WORKSPACE_DIR is not set." >&2
  exit 1
fi

# ── Create workspace directories ──────────────────────────────────────────────
echo "Creating workspace layout at:"
echo "  ${WORKSPACE_DIR}/"
echo ""

mkdir -p "${WORKSPACE_DIR}"

subdirs=("runs" "logs" "reports" "artifacts" "scratch" "tmp")
for d in "${subdirs[@]}"; do
  mkdir -p "${WORKSPACE_DIR}/${d}"
  echo "  mkdir  ${WORKSPACE_DIR}/${d}"
done
echo ""

# ── Check write permissions ───────────────────────────────────────────────────
if [[ -w "${WORKSPACE_DIR}" ]]; then
  echo "  Write permissions  : OK"
else
  echo "ERROR: No write permission on ${WORKSPACE_DIR}" >&2
  exit 1
fi

# ── Validate spec path ────────────────────────────────────────────────────────
if [[ -n "$SPEC_PATH" ]]; then
  if [[ -e "$SPEC_PATH" ]]; then
    SIZE=$(du -sh "${SPEC_PATH}" 2>/dev/null | cut -f1 || echo "?")
    echo "  Spec file          : OK (${SIZE})"
  else
    echo "  WARNING: Spec path does not exist: ${SPEC_PATH}" >&2
  fi
else
  echo "  Spec path          : (not set — skipping check)"
fi

# ── Write workspace.yaml ──────────────────────────────────────────────────────
cat > "${WORKSPACE_DIR}/workspace.yaml" <<YAML
# DV Skills Workspace Configuration
project_name:  "${PROJECT_NAME}"
workspace_dir: "${WORKSPACE_DIR}"
spec_path:     "${SPEC_PATH:-}"
created_at:    "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

directories:
  runs:      "${WORKSPACE_DIR}/runs"
  logs:      "${WORKSPACE_DIR}/logs"
  reports:   "${WORKSPACE_DIR}/reports"
  artifacts: "${WORKSPACE_DIR}/artifacts"
YAML
echo "  workspace.yaml     : written"

# ── Disk space check ─────────────────────────────────────────────────────────
FREE=$(df -h "${WORKSPACE_DIR}" 2>/dev/null | awk 'NR==2{print $4}' || echo "?")
echo ""
echo "  Free disk space    : ${FREE}"
echo ""
echo "✓  Workspace ready at ${WORKSPACE_DIR}"
