#!/bin/sh
# Inject non-secret runtime config for the separated operator UI
# (US-093 / US-094 / US-097 / US-099).
# apiBaseUrl + envLabel (uat|prod) + googleAuthEnabled — never embed API keys or tokens.
# US-099: when apiBaseUrl is "/" or "same-origin", browser uses same-origin private hop
# (nginx proxies typed-client + /auth/* to the private worker).
set -eu

escape_js_string() {
  # Escape backslash and double-quote for a JSON string literal.
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

API_BASE="$(escape_js_string "${SILVERMAN_OPERATOR_UI_API_BASE_URL:-}")"
ENV_LABEL="$(escape_js_string "${SILVERMAN_OPERATOR_UI_ENV_LABEL:-}")"

# Non-secret enablement flag only (true/false). Client secrets stay on the worker.
case "$(printf '%s' "${SILVERMAN_OPERATOR_GOOGLE_AUTH_ENABLED:-false}" | tr '[:upper:]' '[:lower:]')" in
  1|true|yes|on) GOOGLE_AUTH="true" ;;
  *) GOOGLE_AUTH="false" ;;
esac

cat > /usr/share/nginx/html/config.js <<EOF
window.__SILVERMAN_OPERATOR_UI_CONFIG__ = {
  "deliveryMode": "separated",
  "apiBaseUrl": "${API_BASE}",
  "envLabel": "${ENV_LABEL}",
  "googleAuthEnabled": ${GOOGLE_AUTH}
};
EOF

# Private UI→API hop upstream (host:port only — no scheme). Default: compose DNS to worker.
# Never point this at a public internet API hostname for Authority Manager.
WORKER_HOSTPORT="${SILVERMAN_OPERATOR_UI_WORKER_UPSTREAM:-silverman-blog-linkedin-worker:8000}"
# Strip accidental scheme if an operator pastes a full URL (keep host:port only).
case "$WORKER_HOSTPORT" in
  http://*|https://*)
    WORKER_HOSTPORT="$(printf '%s' "$WORKER_HOSTPORT" | sed -E 's#^https?://##; s#/.*##')"
    ;;
esac
export SILVERMAN_OPERATOR_UI_WORKER_UPSTREAM_HOSTPORT="$WORKER_HOSTPORT"

TEMPLATE="/etc/nginx/templates/default.conf.template"
TARGET="/etc/nginx/conf.d/default.conf"
if [ -f "$TEMPLATE" ]; then
  # Substitute only the upstream placeholder; preserve nginx $variables.
  envsubst '${SILVERMAN_OPERATOR_UI_WORKER_UPSTREAM_HOSTPORT}' < "$TEMPLATE" > "$TARGET"
fi

exec nginx -g "daemon off;"
