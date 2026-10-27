#!/bin/bash
set -euo pipefail
if [[ -f .env ]]; then
	set -a
	source .env
	set +a
fi
python3 app.py LOCAL 5302
