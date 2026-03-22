#!/usr/bin/env python3
"""
check_environment.py — DV Skills common environment checker
Run this before any DV skill that requires Python dependencies.

Usage:
    python3 check_environment.py                  # check all
    python3 check_environment.py --skill s1       # check S1 deps only
    python3 check_environment.py --skill s2       # check S2 deps only
    python3 check_environment.py --install        # auto-install missing
"""

import sys
import subprocess
import argparse

# ── Dependency map per skill ───────────────────────────────────────────────────
DEPS = {
    "s1": [
        ("json",      None,       "stdlib"),
        ("pathlib",   None,       "stdlib"),
        ("datetime",  None,       "stdlib"),
    ],
    "s2": [
        ("openpyxl",  "openpyxl", "pip"),
        ("json",      None,       "stdlib"),
        ("pathlib",   None,       "stdlib"),
    ],
    "s3": [
        ("openpyxl",   "openpyxl",   "pip"),   # read S2 testplan
        ("graphviz",   "graphviz",   "pip"),   # TB architecture diagram
        ("matplotlib", "matplotlib", "pip"),   # Gantt + coverage charts
        ("PIL",        "Pillow",     "pip"),   # image handling
        # PDF: weasyprint or reportlab as pandoc fallback
        # pandoc is a system tool — checked separately below
    ],
    "s4": [
        ("json",      None,       "stdlib"),
        ("pathlib",   None,       "stdlib"),
        ("datetime",  None,       "stdlib"),
        ("stat",      None,       "stdlib"),
        # No pip deps — all generation is stdlib only
    ],
    "s5": [
        ("json",      None,       "stdlib"),
        ("pathlib",   None,       "stdlib"),
        ("datetime",  None,       "stdlib"),
        ("textwrap",  None,       "stdlib"),
        ("openpyxl",  "openpyxl", "pip"),   # read S2 testplan for assertions/checkers
        ("graphviz",  "graphviz", "pip"),   # VIP hierarchy diagrams
    ],
    "s6": [
        ("json",      None,       "stdlib"),
        ("pathlib",   None,       "stdlib"),
        ("datetime",  None,       "stdlib"),
        ("re",        None,       "stdlib"),
        ("openpyxl",  "openpyxl", "pip"),   # parse testplan.xlsx
    ],
}

ALL_DEPS = {pkg: install for skill_deps in DEPS.values()
            for pkg, install, _ in skill_deps if install}


def check_dep(import_name, install_name, source):
    try:
        __import__(import_name)
        return True, None
    except ImportError:
        return False, install_name


def install_dep(package):
    print(f"  Installing {package}...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", package, "-q"],
        capture_output=True, text=True
    )
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="DV Skills environment checker")
    parser.add_argument("--skill", choices=["s1","s2","s3","s4","s5","s6","all"], default="all",
                        help="Which skill to check dependencies for")
    parser.add_argument("--install", action="store_true",
                        help="Auto-install missing pip packages")
    args = parser.parse_args()

    skills_to_check = list(DEPS.keys()) if args.skill == "all" else [args.skill]

    print("=" * 56)
    print(f"  DV Skills — Environment Check")
    print(f"  Python: {sys.version.split()[0]}  |  Executable: {sys.executable}")
    print("=" * 56)

    all_ok = True
    missing = []

    for skill in skills_to_check:
        if skill not in DEPS:
            continue
        print(f"\n  [{skill.upper()}] Dependencies:")
        for import_name, install_name, source in DEPS[skill]:
            ok, pkg = check_dep(import_name, install_name, source)
            status = "✓" if ok else "✗"
            note   = f"(stdlib)" if source == "stdlib" else f"(pip: {install_name})"
            print(f"    {status}  {import_name:<18} {note}")
            if not ok:
                all_ok = False
                missing.append(install_name)

    # ── System tool checks (for s3) ───────────────────────────────────────────
    if args.skill in ("s3", "s5", "s6", "all"):
        print("\n  [S3] System tools:")
        for tool, desc in [("pandoc", "PDF generation (primary)"),
                            ("dot",   "Graphviz binary (diagrams)")]:
            result = subprocess.run(["which", tool], capture_output=True)
            found = result.returncode == 0
            status = "✓" if found else "⚠"
            note   = "found" if found else f"NOT FOUND — install via: brew install {tool}"
            print(f"    {status}  {tool:<18} {note}  ({desc})")
            if not found and tool == "pandoc":
                print("       Fallback: weasyprint or reportlab will be used automatically")

    print()
    if all_ok:
        print("  ✓ All dependencies satisfied.\n")
        sys.exit(0)
    else:
        print(f"  ✗ Missing packages: {', '.join(missing)}")
        if args.install:
            print()
            success = True
            for pkg in missing:
                if pkg and not install_dep(pkg):
                    print(f"  ✗ Failed to install {pkg}")
                    success = False
            if success:
                print("  ✓ All packages installed successfully.\n")
                sys.exit(0)
            else:
                print("  Some installations failed. Run manually:\n")
                print(f"    pip3 install {' '.join(missing)}\n")
                sys.exit(1)
        else:
            print("\n  To install missing packages, run:")
            print(f"    pip3 install {' '.join(missing)}")
            print("  Or re-run with --install flag.\n")
            sys.exit(1)


if __name__ == "__main__":
    main()
