#!/usr/bin/env python3
"""
Costco Markdown Hunter - Build Script
======================================
Compiles the app to a standalone Windows executable using Nuitka.

Usage:
    python build.py          # Build executable
    python build.py --test   # Test run without building
"""

import subprocess
import sys
from pathlib import Path

# Build configuration
APP_NAME = "CostcoMarkdownHunter"
VERSION = "1.0.0"
MAIN_SCRIPT = "app.py"
OUTPUT_DIR = "dist"

# Data files to include (flat structure)
DATA_FILES = [
    "costco_warehouses_master.json",
    "production_markdowns.json",
    "warehouse_runner_optimized_markdowns.json",
]

# Nuitka options
NUITKA_OPTIONS = [
    "--standalone",
    "--onefile",
    "--windows-disable-console",
    "--enable-plugin=tk-inter",
    "--include-package=customtkinter",
    f"--output-filename={APP_NAME}.exe",
    f"--output-dir={OUTPUT_DIR}",
    "--assume-yes-for-downloads",
    "--remove-output",
]


def check_nuitka():
    """Check if Nuitka is installed."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "nuitka", "--version"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"[OK] Nuitka found: {result.stdout.strip()}")
            return True
    except:
        pass

    print("[!] Nuitka not found. Installing...")
    subprocess.run([sys.executable, "-m", "pip", "install", "nuitka", "ordered-set"])
    return True


def build():
    """Run the Nuitka build."""
    print("=" * 60)
    print(f"Building {APP_NAME} v{VERSION}")
    print("=" * 60)

    product_dir = Path(__file__).parent

    if not check_nuitka():
        return False

    # Check required files
    print("\n[*] Checking files...")

    if not (product_dir / MAIN_SCRIPT).exists():
        print(f"[!] Missing: {MAIN_SCRIPT}")
        return False
    print(f"    {MAIN_SCRIPT}: OK")

    # Add data files to build
    for df in DATA_FILES:
        if (product_dir / df).exists():
            NUITKA_OPTIONS.append(f"--include-data-files={df}={df}")
            print(f"    {df}: OK")
        else:
            print(f"    {df}: MISSING (optional)")

    # Build command
    cmd = [
        sys.executable, "-m", "nuitka",
        *NUITKA_OPTIONS,
        MAIN_SCRIPT
    ]

    print(f"\n[*] Build command:")
    print(f"    {' '.join(cmd)}\n")

    print("[*] Starting build (this takes 5-15 minutes)...\n")
    result = subprocess.run(cmd, cwd=product_dir)

    if result.returncode == 0:
        exe_path = product_dir / OUTPUT_DIR / f"{APP_NAME}.exe"
        print("\n" + "=" * 60)
        print(f"[OK] Build successful!")
        print(f"     Executable: {exe_path}")
        if exe_path.exists():
            print(f"     Size: {exe_path.stat().st_size / 1024 / 1024:.1f} MB")
        print("=" * 60)
        return True
    else:
        print("\n[X] Build failed!")
        return False


def test_run():
    """Test run the app without building."""
    print("[*] Test running app.py...")
    product_dir = Path(__file__).parent
    subprocess.run([sys.executable, str(product_dir / "app.py")])


if __name__ == "__main__":
    if "--test" in sys.argv:
        test_run()
    else:
        build()
