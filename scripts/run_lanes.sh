#!/usr/bin/env bash
# Run the four video lanes. Keys come from the environment only.
set -euo pipefail

cd "$(dirname "$0")/.."
OUT="reports/lanes"
mkdir -p "$OUT"

need_key() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    echo "missing $name — export it in this shell, do not write it to a file" >&2
    exit 1
  fi
}

for key in OPENAI_API_KEY GEMINI_API_KEY ANTHROPIC_API_KEY DEEPSEEK_API_KEY; do
  need_key "$key"
done

run_lane() {
  local name="$1" model="$2" prompt="$3"
  echo "== $name ($model)"
  if ! opencode run -m "$model" "$prompt" > "$OUT/$name.md" 2>&1; then
    echo "lane $name failed; not recording it" >&2
    exit 1
  fi
  if [ ! -s "$OUT/$name.md" ]; then
    echo "lane $name produced no output" >&2
    exit 1
  fi
  echo "   wrote $OUT/$name.md"
}

run_lane 1-chatgpt openai/gpt-5.5 \
  "Read simulator/exchange/exchange.py and tests/test_withdraw_atomicity.py. In at most 5 bullets: what order the old withdraw used, why a rejected withdrawal could still broadcast (S1), and which assertion catches it. Do not edit files."

run_lane 2-gemini google/gemini-3.8-flash \
  "Read simulator/security.py. Find three ways a withdrawal could bypass the controls. For each: function, bypass, and the test that should catch it. At most 5 bullets. Do not edit files."

run_lane 3-claude anthropic/claude-sonnet-5 \
  "Read simulator/exchange/exchange.py withdraw(). Verify the order authorize -> debit -> broadcast and the refund path. Name one remaining failure mode. At most 5 bullets. Do not edit files."

run_lane 4-deepseek deepseek/deepseek-v4-pro \
  "Run .venv/bin/python scripts/show_replay.py and .venv/bin/python scripts/verify_all.py. Report the rejected withdrawal numbers, the test counts, and one limitation. At most 5 bullets. Do not edit files."

echo "all four lanes wrote to $OUT"
