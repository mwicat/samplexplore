#!/bin/bash

set -Eeuo pipefail

python -m poetry run python -m briefcase create
python -m poetry run python -m briefcase build
