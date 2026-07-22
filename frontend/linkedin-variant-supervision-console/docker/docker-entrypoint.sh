#!/bin/sh
# Inject non-secret runtime config for the separated operator UI (US-093 / US-094).
# apiBaseUrl + envLabel (uat|prod) — never embed API keys or tokens.
set -eu

escape_js_string() {
  # Escape backslash and double-quote for a JSON string literal.
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

API_BASE="$(escape_js_string "${SILVERMAN_OPERATOR_UI_API_BASE_URL:-}")"
ENV_LABEL="$(escape_js_string "${SILVERMAN_OPERATOR_UI_ENV_LABEL:-}")"

cat > /usr/share/nginx/html/config.js <<EOF
window.__SILVERMAN_OPERATOR_UI_CONFIG__ = {
  "deliveryMode": "separated",
  "apiBaseUrl": "${API_BASE}",
  "envLabel": "${ENV_LABEL}"
};
EOF

exec nginx -g "daemon off;"
