#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# run_chipagent_identity.bash
# DV Skills GUI — Project Identity section
#
# Environment variables injected by the GUI backend:
#   PROJECT_NAME   WORKSPACE_DIR   USER_NAME   GITHUB_REPO
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT_NAME="${PROJECT_NAME:-}"
WORKSPACE_DIR="${WORKSPACE_DIR:-}"
USER_NAME="${USER_NAME:-}"
GITHUB_REPO="${GITHUB_REPO:-}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ChipAgent — Project Identity"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Project  : ${PROJECT_NAME:-(not set)}"
echo "  Engineer : ${USER_NAME:-(not set)}"
echo "  GitHub   : ${GITHUB_REPO:-(not set)}"
echo "  Workspace: ${WORKSPACE_DIR:-(not set)}"
echo ""

# ── Validate required inputs ──────────────────────────────────────────────────
if [[ -z "$PROJECT_NAME" ]]; then
  echo "ERROR: PROJECT_NAME is not set. Fill in 'Project Name' and retry." >&2
  exit 1
fi
if [[ -z "$WORKSPACE_DIR" ]]; then
  echo "ERROR: WORKSPACE_DIR is not set. Fill in 'Workspace Directory' and retry." >&2
  exit 1
fi

ROOT="${WORKSPACE_DIR}/${PROJECT_NAME}"

# ── Create DV project directory scaffold ─────────────────────────────────────
echo "Creating project scaffold at:"
echo "  ${ROOT}/"
echo ""

dirs=(
  "rtl"
  "dv/tb"
  "dv/sequences"
  "dv/tests"
  "dv/assertions"
  "dv/coverage"
  "dv/regression"
  "dv/reports"
  "dv/scripts"
  "dv/evals"
  "doc"
  "sim"
)

for d in "${dirs[@]}"; do
  mkdir -p "${ROOT}/${d}"
  echo "  mkdir  ${ROOT}/${d}"
done
echo ""

# ── Git init ──────────────────────────────────────────────────────────────────
cd "${ROOT}"
if [[ ! -d ".git" ]]; then
  git init -q
  echo "  git init — done"
else
  echo "  git repo already exists — skipping init"
fi

# ── .gitignore ────────────────────────────────────────────────────────────────
cat > .gitignore <<'GITIGNORE'
# Simulation artifacts
*.vdb/
simv*
csrc/
urgReport/
DVEfiles/
*.fsdb
*.vpd
*.vcd
*.log
*.rc

# Python
__pycache__/
*.pyc
*.pyo
.venv/

# Editor
.DS_Store
*.swp
*~
GITIGNORE
echo "  .gitignore — written"

# ── README ───────────────────────────────────────────────────────────────────
cat > README.md <<README
# ${PROJECT_NAME}

**Engineer:** ${USER_NAME:-TBD}
**Repository:** ${GITHUB_REPO:-TBD}

## DV Directory Layout

\`\`\`
${PROJECT_NAME}/
├── rtl/              RTL source files
├── dv/
│   ├── tb/           UVM testbench
│   ├── sequences/    UVM sequences & virtual sequences
│   ├── tests/        UVM test classes
│   ├── assertions/   SVA bind modules
│   ├── coverage/     Coverage closure files & exclusions
│   ├── regression/   Regression lists & scripts
│   ├── reports/      HTML regression & sign-off reports
│   └── scripts/      Helper scripts
├── doc/              Specifications & guidelines
└── sim/              Simulation run directory
\`\`\`

## Generated with DV Skills GUI
README
echo "  README.md — written"

# ── project_config snapshot ──────────────────────────────────────────────────
cat > project_config.json <<JSON
{
  "project_name": "${PROJECT_NAME}",
  "user_name":    "${USER_NAME:-}",
  "github_repo":  "${GITHUB_REPO:-}",
  "workspace_dir":"${WORKSPACE_DIR}",
  "created_at":   "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON
echo "  project_config.json — written"

# ── Remote origin (if GitHub repo provided) ────────────────────────────────
if [[ -n "$GITHUB_REPO" ]]; then
  if git remote get-url origin &>/dev/null; then
    echo "  git remote origin already configured"
  else
    git remote add origin "${GITHUB_REPO}"
    echo "  git remote add origin ${GITHUB_REPO}"
  fi
fi

echo ""
echo "✓  Project '${PROJECT_NAME}' initialised — engineer: ${USER_NAME:-(not set)}"
