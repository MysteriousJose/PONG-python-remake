#!/bin/bash
set -e

echo "Creating Python virtual environment..."
python -m venv .venv

echo "Installing dependencies..."
.venv/bin/python -m pip install -r requirements.txt

echo "Applying CMU Graphics FreeType compatibility fix..."
ln -sf /usr/lib/libfreetype.so.6 \
    .venv/lib/python3.13/site-packages/cmu_graphics_helpers.libs/libfreetype-c0e61f0c.so.6

echo "Setup complete!"
echo "Run the game with: .venv/bin/python pong.py"