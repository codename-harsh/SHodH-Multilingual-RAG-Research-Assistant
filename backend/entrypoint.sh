#!/bin/sh
set -eu
cd /app
alembic upgrade head
exec "$@"
