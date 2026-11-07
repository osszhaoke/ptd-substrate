#!/bin/sh
set -eu
exec python3 -B -I "$(dirname "$0")/verify_release.py"
