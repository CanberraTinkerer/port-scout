#!/usr/bin/with-contenv bashio
# ==============================================================================
# Home Assistant Add-on: Port Scout
# Runs the Port Scout FastAPI service
# ==============================================================================

PORT=$(bashio::config 'port')
MIN_PORT=$(bashio::config 'min_port')
MAX_PORT=$(bashio::config 'max_port')

bashio::log.info "Starting Port Scout on port ${PORT}..."
bashio::log.info "Default allocation range: ${MIN_PORT} - ${MAX_PORT}"

export PORT_SCOUT_PORT="${PORT}"
export PORT_SCOUT_HOST="0.0.0.0"
export DEFAULT_MIN_PORT="${MIN_PORT}"
export DEFAULT_MAX_PORT="${MAX_PORT}"

cd /app
exec python3 -m app.main
