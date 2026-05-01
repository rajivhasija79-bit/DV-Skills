# HBM-DDR Studio — quick setup from the zip

Prefer the zip over `git clone` if you just want the runnable app and don't
care about repo history.

## 1. Download the zip

Two ways:

- **Direct link** (always pulls latest from `main`):
  ```
  https://github.com/rajivhasija79-bit/DV-Skills/raw/main/hbm-ddr-studio.zip
  ```
  Or with `wget` / `curl`:
  ```bash
  curl -LO https://github.com/rajivhasija79-bit/DV-Skills/raw/main/hbm-ddr-studio.zip
  ```

- **Browse to the file on GitHub** and click the "Download raw file" button
  next to `hbm-ddr-studio.zip`.

The zip is small (~160 KB) — it contains source only. No bundled
`node_modules`, no Python venv, no compiled artifacts (those would have been
~150 MB and would be wrong-architecture for your machine anyway).

## 2. Unzip

```bash
unzip hbm-ddr-studio.zip
cd hbm-ddr-studio
```

## 3. Install dependencies (no sudo needed)

### Python — use your existing venv, or make one in-place

```bash
# Option A: your existing venv
source ~/myvenv/bin/activate
pip install -r backend/requirements.txt

# Option B: a fresh venv inside the project
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
```

Python ≥ 3.9 required.

### Node.js — install user-level if you don't have it

If you already have Node 18+: skip this.

```bash
# nvm (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
exec $SHELL
nvm install 20

# Then in the project:
cd frontend
npm install
cd ..
```

## 4. Run

```bash
./launch.sh        # backend on :8000, frontend on :5173
```

Then open http://localhost:5173 in your browser.

If you're on a remote Linux box, tunnel from your laptop:
```bash
ssh -L 5173:localhost:5173 -L 8000:localhost:8000 user@server
```

## What's in the zip

- `backend/`        — FastAPI app, task YAMLs, dummy scripts, PM mock data, adapter stubs
- `frontend/`       — Vite + React + TypeScript source
- `docs/INTEGRATION.md` — how to plug your own tools into each task / dashboard
- `launch.sh`       — start both servers
- `README.md`       — original project notes

## What's NOT in the zip (and why)

| Excluded                       | Why                                                   |
|--------------------------------|-------------------------------------------------------|
| `backend/.venv/`, `.venv/`     | Architecture-specific Python wheels (mac vs linux)    |
| `frontend/node_modules/`       | Architecture-specific native deps; `npm install` rebuilds |
| `frontend/dist/`, `.vite/`     | Build artifacts; regenerated on `npm run build`       |
| `__pycache__/`, `*.pyc`        | Python bytecode cache                                 |
| `backend/runs/`, `jobstore.sqlite` | Per-user runtime state                            |
| tsc-emitted `*.js` next to `*.tsx` | Build artifacts; Vite handles TS at dev/build time |

## Updating to the latest version

Just download the zip again and `unzip -o hbm-ddr-studio.zip` (overwrite).
Your `backend/.venv/` and `frontend/node_modules/` stay put because they're
not in the zip.
