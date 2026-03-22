#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# run_chipagent_tools.bash
# DV Skills GUI — EDA Tools section
#
# Environment variables injected by the GUI backend:
#   EDA_TOOL   EDA_TOOL_PATH   LICENSE_SERVER
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

EDA_TOOL="${EDA_TOOL:-vcs}"
EDA_TOOL_PATH="${EDA_TOOL_PATH:-}"
LICENSE_SERVER="${LICENSE_SERVER:-}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ChipAgent — EDA Tool Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Tool     : ${EDA_TOOL}"
echo "  Path     : ${EDA_TOOL_PATH:-(not set)}"
echo "  Licence  : ${LICENSE_SERVER:-(not set)}"
echo ""

if [[ -z "$EDA_TOOL_PATH" ]]; then
  echo "ERROR: EDA_TOOL_PATH is not set." >&2
  exit 1
fi

# ── Path existence ────────────────────────────────────────────────────────────
if [[ -d "$EDA_TOOL_PATH" ]]; then
  echo "  Install path       : EXISTS (directory)"
elif [[ -f "$EDA_TOOL_PATH" ]]; then
  echo "  Install path       : EXISTS (file)"
else
  echo "ERROR: EDA_TOOL_PATH does not exist: ${EDA_TOOL_PATH}" >&2
  exit 1
fi

# ── Tool-specific binary check ────────────────────────────────────────────────
case "${EDA_TOOL,,}" in
  vcs)
    BIN="${EDA_TOOL_PATH}/bin/vcs"
    BIN_NAME="vcs"
    ;;
  questa)
    BIN="${EDA_TOOL_PATH}/bin/vsim"
    BIN_NAME="vsim"
    ;;
  xcelium)
    BIN="${EDA_TOOL_PATH}/bin/xrun"
    BIN_NAME="xrun"
    ;;
  *)
    BIN="${EDA_TOOL_PATH}/bin/${EDA_TOOL}"
    BIN_NAME="${EDA_TOOL}"
    ;;
esac

echo "  Checking binary    : ${BIN}"
if [[ -x "$BIN" ]]; then
  echo "  Binary             : FOUND"
  VERSION=$("${BIN}" -full64 -ID 2>&1 | head -3 || "${BIN}" --version 2>&1 | head -3 || echo "(version query failed)")
  echo "  Version info       : ${VERSION}"
else
  echo "  WARNING: Binary not found or not executable: ${BIN}"
  echo "  (This may be expected in demo environments)"
fi

# ── Licence server check ──────────────────────────────────────────────────────
if [[ -n "$LICENSE_SERVER" ]]; then
  echo ""
  echo "  Licence server     : ${LICENSE_SERVER}"
  # Parse port@host
  PORT=$(echo "${LICENSE_SERVER}" | cut -d@ -f1)
  HOST=$(echo "${LICENSE_SERVER}" | cut -d@ -f2)
  if [[ "$PORT" =~ ^[0-9]+$ && -n "$HOST" ]]; then
    echo "  Testing connection : ${HOST}:${PORT}"
    if command -v nc &>/dev/null; then
      if nc -z -w 3 "${HOST}" "${PORT}" 2>/dev/null; then
        echo "  Port reachable     : OK"
      else
        echo "  WARNING: Cannot reach ${HOST}:${PORT} — check VPN / firewall"
      fi
    else
      echo "  (nc not available — skipping port test)"
    fi
  else
    echo "  (Could not parse host:port from '${LICENSE_SERVER}')"
  fi
else
  echo "  Licence server     : (not set — skipping)"
fi

echo ""
echo "✓  ${EDA_TOOL} verification complete"
