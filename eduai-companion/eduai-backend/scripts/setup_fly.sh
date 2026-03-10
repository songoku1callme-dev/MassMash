#!/usr/bin/env bash
# ============================================================
# Lumnos Backend — Fly.io Setup Script
# ============================================================
# Run this ONCE to provision the Fly.io app, database, volume,
# and secrets.  Requires: flyctl CLI authenticated (`fly auth login`).
#
# Usage:
#   chmod +x scripts/setup_fly.sh
#   ./scripts/setup_fly.sh
# ============================================================

set -euo pipefail

APP_NAME="lumnos-backend"
DB_NAME="lumnos-db"
REGION="fra"  # Frankfurt

echo "=== 1/5  Creating Fly.io app ==="
flyctl apps create "$APP_NAME" --machines || echo "App may already exist"

echo ""
echo "=== 2/5  Creating Postgres cluster ==="
flyctl postgres create \
  --name "$DB_NAME" \
  --region "$REGION" \
  --vm-size shared-cpu-1x \
  --volume-size 10 \
  || echo "Postgres cluster may already exist"

echo ""
echo "=== 3/5  Attaching Postgres to app ==="
flyctl postgres attach "$DB_NAME" --app "$APP_NAME" \
  || echo "Already attached"

echo ""
echo "=== 4/5  Creating persistent volume ==="
flyctl volumes create lumnos_data \
  --app "$APP_NAME" \
  --region "$REGION" \
  --size 1 \
  || echo "Volume may already exist"

echo ""
echo "=== 5/5  Setting secrets ==="
echo "  (Replace placeholder values with real keys before running)"
flyctl secrets set \
  --app "$APP_NAME" \
  SECRET_KEY="CHANGE_ME_RANDOM_64_CHARS" \
  GROQ_API_KEY="gsk_..." \
  CLERK_SECRET_KEY="sk_live_..." \
  STRIPE_SECRET_KEY="sk_live_..." \
  STRIPE_WEBHOOK_SECRET="whsec_..." \
  TAVILY_API_KEY="tvly-..." \
  RESEND_API_KEY="re_..." \
  LUMNOS_DEV_MODE="0"

echo ""
echo "=== Done! ==="
echo "Next steps:"
echo "  1. Replace placeholder secrets above with real values"
echo "  2. Deploy: flyctl deploy --remote-only"
echo "  3. Verify: flyctl status --app $APP_NAME"
echo "  4. Logs:   flyctl logs --app $APP_NAME"
