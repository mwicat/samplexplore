#!/bin/bash

python -m poetry run python -m PyInstaller \
  --noconfirm \
  --icon resources/headphones.png \
  --onefile \
  --windowed \
  --name samplexplore \
  --collect-all sample_explorer \
  pyinstaller/runscript.py
