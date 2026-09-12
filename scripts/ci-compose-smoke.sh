#!/bin/sh
set -eu

frontend_url="${FRONTEND_URL:-http://127.0.0.1:3000}"
backend_url="${BACKEND_URL:-http://127.0.0.1:8000}"
work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

curl --fail --silent --show-error "$frontend_url/healthz" > /dev/null
curl --fail --silent --show-error "$backend_url/api/v1/health/ready" > /dev/null
curl --fail --silent --show-error "$frontend_url/api/v1/health/ready" > /dev/null

assert_headers() {
  url="$1"
  expected_status="$2"
  headers="$work_dir/headers"
  status="$(curl --silent --show-error --output /dev/null --dump-header "$headers" --write-out '%{http_code}' "$url")"
  test "$status" = "$expected_status"
  tr -d '\r' < "$headers" | grep -Eiq '^content-security-policy:'
  tr -d '\r' < "$headers" | grep -Eiq '^x-content-type-options: nosniff$'
  tr -d '\r' < "$headers" | grep -Eiq '^x-frame-options: deny$'
  tr -d '\r' < "$headers" | grep -Eiq '^referrer-policy: strict-origin-when-cross-origin$'
  tr -d '\r' < "$headers" | grep -Eiq '^permissions-policy:'
  tr -d '\r' < "$headers" | grep -Eiq '^cross-origin-opener-policy: same-origin$'
  if tr -d '\r' < "$headers" | grep -Eiq '^server: .+/[0-9]'; then
    echo "Server version is exposed by $url" >&2
    return 1
  fi
}

assert_headers "$frontend_url/" 200
assert_headers "$frontend_url/api/v1/health/ready" 200
assert_headers "$frontend_url/assets/not-present.js" 404

curl --silent --show-error --dump-header "$work_dir/index-headers" --output "$work_dir/index" "$frontend_url/"
tr -d '\r' < "$work_dir/index-headers" | grep -Eiq '^cache-control: no-cache$'
asset="$(grep -Eo '/assets/[^" ]+\.(js|css)' "$work_dir/index" | sed -n '1p')"
test -n "$asset"
curl --fail --silent --show-error --dump-header "$work_dir/asset-headers" --output /dev/null "$frontend_url$asset"
tr -d '\r' < "$work_dir/asset-headers" | grep -Eiq '^cache-control: public, max-age=31536000, immutable$'

test "$(docker compose exec -T backend id -u)" -ne 0
test "$(docker compose exec -T frontend id -u)" -ne 0
