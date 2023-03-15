#!/bin/bash

python -m poetry run python -m PyInstaller \
  --noconfirm \
  --icon resources/headphones.png \
  --windowed \
  --name samplexplore \
  --collect-all sample_explorer \
  pyinstaller/runscript.py
