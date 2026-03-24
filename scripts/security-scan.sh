#!/bin/bash
# ContraRed Security Scan — run locally or in CI
set -e

echo "=== Python Dependency Audit ==="
cd backend
pip-audit --requirement requirements.txt --desc 2>&1 || echo "⚠️ Python audit found issues"
cd ..

echo ""
echo "=== Dashboard npm Audit ==="
cd dashboard
npm audit --audit-level=high 2>&1 || echo "⚠️ Dashboard audit found issues"
cd ..

echo ""
echo "=== Word Add-in npm Audit ==="
cd ContraRed-PoC
npm audit --audit-level=high 2>&1 || echo "⚠️ Add-in audit found issues"
cd ..

echo ""
echo "=== Scan Complete ==="
