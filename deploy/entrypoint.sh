#!/bin/sh
# Substitute DRCLAW_PORT in supervisord template and start supervisord.
# Default port 8088; override at runtime with -e DRCLAW_PORT=3000
# (QWENPAW_PORT / COPAW_PORT still accepted as legacy fallbacks).
set -e

_first_set() {
  for name in "$@"; do
    eval "v=\${$name-}"
    if [ -n "$v" ]; then
      printf '%s' "$v"
      return 0
    fi
  done
  return 1
}

is_auth_enabled() {
  flag="$(_first_set DRCLAW_AUTH_ENABLED QWENPAW_AUTH_ENABLED COPAW_AUTH_ENABLED || true)"
  [ -z "$flag" ] && return 1
  flag="$(printf '%s' "$flag" | tr '[:upper:]' '[:lower:]')"
  [ "$flag" = "true" ] || [ "$flag" = "1" ] || [ "$flag" = "yes" ]
}

warn_if_auth_off_container_bind() {
  if is_auth_enabled; then
    return
  fi

  cat >&2 <<EOF
============================================================
SECURITY NOTICE: Dr.Claw is running in Docker without authentication.

Dr.Claw cannot verify whether access to the service is limited to a trusted
network. Anyone who can reach the service may access Dr.Claw APIs without login.

Recommended:
  - Restrict access to a trusted network or protected environment.
  - Enable authentication with DRCLAW_AUTH_ENABLED=true if untrusted users or
    processes may reach the service (QWENPAW_AUTH_ENABLED still accepted).
============================================================
EOF
}

DRCLAW_WORKING_DIR="$(_first_set DRCLAW_WORKING_DIR QWENPAW_WORKING_DIR COPAW_WORKING_DIR || true)"
DRCLAW_WORKING_DIR="${DRCLAW_WORKING_DIR:-/app/working}"
export DRCLAW_WORKING_DIR

# Auto-initialize if config.json is missing (bind mount with empty directory).
if [ ! -f "${DRCLAW_WORKING_DIR}/config.json" ]; then
  echo "⚠️  No config.json found in ${DRCLAW_WORKING_DIR}"
  echo "📦 Running initialization..."
  drclaw init --defaults --accept-security
  echo "✅ Initialization complete!"
else
  echo "✓ Config found in ${DRCLAW_WORKING_DIR}, skipping initialization."
fi

export DRCLAW_PORT="$(_first_set DRCLAW_PORT QWENPAW_PORT COPAW_PORT || true)"
DRCLAW_PORT="${DRCLAW_PORT:-8088}"
export DRCLAW_PORT

warn_if_auth_off_container_bind
envsubst '${DRCLAW_PORT}' \
  < /etc/supervisor/conf.d/supervisord.conf.template \
  > /etc/supervisor/conf.d/supervisord.conf
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
