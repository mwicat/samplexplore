#!/bin/bash

set -Eeuo pipefail

python -m poetry run python setup.py build

