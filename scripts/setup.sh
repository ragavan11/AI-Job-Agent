#!/usr/bin/env bash
# Generates a shared API_AUTH_TOKEN and writes it into all three env files
# so the backend and frontend agree on it automatically. Safe to re-run —
# it won't overwrite files that already exist.
set -euo pipefail
cd "$(dirname "$0")/.."

TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || node -e "console.log(require('crypto').randomBytes(32).toString('base64url'))")

write_if_missing() {
  local target=$1
  local example=$2
  if [ -f "$target" ]; then
    echo "  skip  $target (already exists)"
  else
    cp "$example" "$target"
    echo "  wrote $target"
  fi
}

echo "Setting up Personal Job Agent..."
write_if_missing ".env" ".env.example"
write_if_missing "backend/.env" "backend/.env.example"
write_if_missing "frontend/.env.local" "frontend/.env.local.example"

# Only inject the generated token into files that still have it blank —
# never overwrite a token someone already set on a previous run.
for f in .env backend/.env; do
  if grep -q "^API_AUTH_TOKEN=$" "$f" 2>/dev/null; then
    sed -i.bak "s/^API_AUTH_TOKEN=$/API_AUTH_TOKEN=${TOKEN}/" "$f" && rm -f "$f.bak"
    echo "  set   API_AUTH_TOKEN in $f"
  fi
done
if grep -q "^NEXT_PUBLIC_API_TOKEN=$" "frontend/.env.local" 2>/dev/null; then
  sed -i.bak "s/^NEXT_PUBLIC_API_TOKEN=$/NEXT_PUBLIC_API_TOKEN=${TOKEN}/" "frontend/.env.local" && rm -f "frontend/.env.local.bak"
  echo "  set   NEXT_PUBLIC_API_TOKEN in frontend/.env.local"
fi

echo ""
echo "Done. Next steps:"
echo "  1. Add your AI provider's API key to backend/.env (ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY)"
echo "  2. Edit backend/app/tracked_companies.json with companies you actually want to track"
echo "  3. Run: docker compose up --build"
echo "  4. Open http://localhost:3000, set up your profile, then click Refresh jobs"
