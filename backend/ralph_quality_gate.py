#!/usr/bin/env python3
"""
Ralph Loop Quality Gate Runner
Run this after every implementation task to verify no regressions.

Usage:
    python ralph_quality_gate.py

Exit codes:
    0 = ALL GATES PASSED
    1 = GATE FAILURE (do not proceed)
"""
import subprocess
import sys
import os
import time

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def run_gate(name: str, cmd: list[str], expected_exit: int = 0) -> bool:
    """Run a quality gate command and check exit code."""
    print(f"\n{BOLD}{'='*60}")
    print(f"GATE: {name}")
    print(f"{'='*60}{RESET}")
    print(f"Running: {' '.join(cmd)}")
    start = time.time()

    result = subprocess.run(
        cmd,
        cwd=BACKEND_DIR,
        capture_output=False,
        text=True,
    )

    elapsed = time.time() - start
    passed = result.returncode == expected_exit

    if passed:
        print(f"\n{GREEN}{BOLD}GATE PASSED: {name} ({elapsed:.1f}s){RESET}")
    else:
        print(f"\n{RED}{BOLD}GATE FAILED: {name} (exit code {result.returncode}, {elapsed:.1f}s){RESET}")

    return passed


def main():
    print(f"{BOLD}ContraRed Ralph Loop Quality Gate{RESET}")
    print(f"Backend dir: {BACKEND_DIR}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    gates = [
        ("App Import Check", [sys.executable, "-c", "from main import app; print('IMPORT OK')"]),
        ("Regression Tests (14 baseline)", [sys.executable, "-m", "pytest", "tests/test_regression.py", "-v", "--tb=short"]),
        ("Full Test Suite", [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"]),
    ]

    results = []
    for name, cmd in gates:
        passed = run_gate(name, cmd)
        results.append((name, passed))
        if not passed:
            print(f"\n{RED}{BOLD}STOPPING: Gate '{name}' failed. Fix before proceeding.{RESET}")
            break

    # Summary
    print(f"\n{BOLD}{'='*60}")
    print("QUALITY GATE SUMMARY")
    print(f"{'='*60}{RESET}")
    all_passed = True
    for name, passed in results:
        icon = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"  {icon}  {name}")
        if not passed:
            all_passed = False

    not_run = len(gates) - len(results)
    if not_run > 0:
        for name, _ in gates[len(results):]:
            print(f"  {YELLOW}SKIP{RESET}  {name}")

    if all_passed:
        print(f"\n{GREEN}{BOLD}ALL GATES PASSED — Safe to commit and proceed.{RESET}")
        return 0
    else:
        print(f"\n{RED}{BOLD}GATE FAILURE — DO NOT commit. Fix the issue first.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
