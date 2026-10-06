#!/usr/bin/env bash
# Smoke test against a running website: proves it answers for real. A built
# image isn't enough, since the traps (static files or fig/ missing from a
# wheel, a venv copied between Pythons, astropy trying a download) pass the
# build and break on the first request.
#
# Usage: scripts/smoke.sh [URL]   (default http://127.0.0.1:8000)
#
# Each response goes to a file and is checked from there: `curl | head`
# under pipefail fails at random when head closes the pipe early.
set -euo pipefail

BASE="${1:-http://127.0.0.1:8000}"
ATTEMPTS="${ATTEMPTS:-60}"

TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

fail() {
  echo "FAILED: $*" >&2
  exit 1
}

# GET a path into a file; fail unless HTTP 200.
get() {
  local path="$1" dest="$2" code
  code=$(curl -sS -o "${dest}" -w '%{http_code}' "${BASE}${path}") || fail "${path}: curl exited ${?}"
  [ "${code}" = "200" ] || fail "${path}: HTTP ${code}"
}

echo "Waiting for ${BASE} (up to ${ATTEMPTS} s)..."
ready=""
for _ in $(seq "${ATTEMPTS}"); do
  if curl -fsS -o /dev/null "${BASE}/api/health" 2>/dev/null; then
    ready="yes"
    break
  fi
  sleep 1
done
[ -n "${ready}" ] || fail "no answer in ${ATTEMPTS} s"

echo "1/4 the page, with its security headers"
curl -sS -D "${TMP}/headers" -o "${TMP}/index.html" "${BASE}/" || fail "/: curl exited ${?}"
grep -q "<title>Accuratum</title>" "${TMP}/index.html" || fail "/: not the site's index.html"
grep -qi "^content-security-policy: default-src 'self'" "${TMP}/headers" || fail "/: no CSP header"

echo "2/4 static files and package images"
get "/js/app.js" "${TMP}/app.js"
get "/locales/pt-BR.json" "${TMP}/pt-BR.json"
get "/api/image/accuratum" "${TMP}/logo.png"
[ "$(head -c 4 "${TMP}/logo.png" | od -An -c | tr -d ' ')" = "211PNG" ] || fail "/api/image/accuratum: not a PNG"

# The real grid, both half-years: astropy offline, the process pool, the
# overlays from fig/ and the PDF all run here.
echo "3/4 a full sundial (Brasília, takes ~15 s)"
start=$(date +%s)
code=$(curl -sS -o "${TMP}/sundial.json" -w '%{http_code}' --max-time 90 \
  -F lat=-15.78 -F lon=-47.92 -F year=2026 \
  -F dayline_color='#d55e00' -F hourline_color='#0072b2' \
  -F title0=Smoke -F subtitle0=p0 -F title1=Smoke -F subtitle1=p1 \
  "${BASE}/api/sundial") || fail "/api/sundial: curl exited ${?}"
[ "${code}" = "200" ] || fail "/api/sundial: HTTP ${code}: $(head -c 300 "${TMP}/sundial.json")"
echo "    $(( $(date +%s) - start )) s"

echo "4/4 two PNGs and a PDF in the answer"
python3 - "${TMP}/sundial.json" <<'EOF' || fail "/api/sundial: unexpected body"
import base64, json, sys
body = json.load(open(sys.argv[1]))
pngs = [base64.b64decode(p) for p in body["pngs"]]
pdf = base64.b64decode(body["pdf"])
assert len(pngs) == 2 and all(p[:4] == b"\x89PNG" for p in pngs), "PNGs"
assert pdf[:4] == b"%PDF" and len(pdf) > 10_000, "PDF"
print(f"    PNGs {[len(p) for p in pngs]} bytes, PDF {len(pdf)} bytes")
EOF

echo "Smoke: all good."
