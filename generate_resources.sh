#!/bin/bash

set -Eeuo pipefail

python -m poetry run pyside2-rcc icons.rc -o src/samplexplore/rc_icons.py
