#!/bin/bash

# CSV Text Processing Tool Launcher
echo "Starting CSV Text Processing Tool..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install requirements if needed
if [ ! -f ".requirements_installed" ]; then
    echo "Installing requirements..."
    pip install -r requirements.txt
    touch .requirements_installed
fi

# Download NLTK data
python3 -c "
import nltk
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)
print('NLTK data downloaded.')
"

# Start the application
echo "Launching application..."
python3 advanced_text_processor.py
