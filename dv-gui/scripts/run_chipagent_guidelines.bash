#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# run_chipagent_guidelines.bash
# DV Skills GUI — Guidelines & Standards section
#
# Environment variables injected by the GUI backend:
#   CODING_GUIDELINES   SOC_INTEG_GUIDELINES   WORKSPACE_DIR
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

CODING_GUIDELINES="${CODING_GUIDELINES:-}"
SOC_INTEG_GUIDELINES="${SOC_INTEG_GUIDELINES:-}"
WORKSPACE_DIR="${WORKSPACE_DIR:-}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ChipAgent — Guidelines & Standards Validation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Coding guidelines  : ${CODING_GUIDELINES:-(not set)}"
echo "  SoC integ guide    : ${SOC_INTEG_GUIDELINES:-(not set)}"
echo ""

ERRORS=0

# ── Helper: validate a doc file ───────────────────────────────────────────────
validate_doc() {
  local LABEL="$1"
  local PATH_VAR="$2"

  if [[ -z "$PATH_VAR" ]]; then
    echo "  ${LABEL}: (not set — skipping)"
    return
  fi

  echo "  ${LABEL}:"
  echo "    Path : ${PATH_VAR}"

  if [[ ! -e "$PATH_VAR" ]]; then
    echo "    ERROR: File not found" >&2
    ERRORS=$((ERRORS + 1))
    return
  fi

  SIZE=$(du -sh "${PATH_VAR}" 2>/dev/null | cut -f1 || echo "?")
  echo "    Size : ${SIZE}  — OK"

  # Word/page count hint
  EXT="${PATH_VAR##*.}"
  case "${EXT,,}" in
    txt|md)
      LINES=$(wc -l < "${PATH_VAR}" 2>/dev/null || echo "?")
      WORDS=$(wc -w < "${PATH_VAR}" 2>/dev/null || echo "?")
      echo "    Lines: ${LINES}  Words: ${WORDS}"
      ;;
    pdf)
      if command -v pdfinfo &>/dev/null; then
        PAGES=$(pdfinfo "${PATH_VAR}" 2>/dev/null | grep Pages | awk '{print $2}' || echo "?")
        echo "    Pages: ${PAGES}"
      fi
      ;;
  esac

  # Copy into workspace doc/ if workspace is set
  if [[ -n "$WORKSPACE_DIR" && -d "$WORKSPACE_DIR" ]]; then
    DEST="${WORKSPACE_DIR}/doc"
    mkdir -p "${DEST}"
    cp "${PATH_VAR}" "${DEST}/" 2>/dev/null && \
      echo "    Copied to: ${DEST}/$(basename "${PATH_VAR}")" || \
      echo "    (copy skipped — same location)"
  fi
}

validate_doc "Coding guidelines   " "${CODING_GUIDELINES}"
echo ""
validate_doc "SoC integ guidelines" "${SOC_INTEG_GUIDELINES}"

# ── Write guidelines index ────────────────────────────────────────────────────
if [[ -n "$WORKSPACE_DIR" && -d "$WORKSPACE_DIR" ]]; then
  cat > "${WORKSPACE_DIR}/doc/guidelines_index.yaml" <<YAML
# DV Guidelines Index
coding_guidelines:      "${CODING_GUIDELINES:-}"
soc_integ_guidelines:   "${SOC_INTEG_GUIDELINES:-}"
validated_at:           "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
YAML
  echo ""
  echo "  guidelines_index.yaml written to ${WORKSPACE_DIR}/doc/"
fi

echo ""
if [[ $ERRORS -gt 0 ]]; then
  echo "ERROR: ${ERRORS} file(s) could not be validated." >&2
  exit 1
fi
echo "✓  All documentation files validated and accessible"
