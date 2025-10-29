#! /bin/bash

export CHAINLIT_HOST=0.0.0.0
export CHAINLIT_PORT=8080

# Check if Python is installed
#PYTHON_CHECK=$(which python3 || which python)
#
#if [ -z "${PYTHON_CHECK}" ]; then
#    echo "Python is not installed. Please install Python 3.8 or higher."
#    exit 1
#fi
#
## Install dependencies if requirements.txt exists
#if [ -f "requirements.txt" ]; then
#    echo "Installing dependencies from requirements.txt..."
#    pip install -r requirements.txt
#else
#    echo "requirements.txt not found. Skipping dependency installation."
#fi

# Install git if not installed
apt-get update
apt-get install git -y

# Run Chainlit app
python -m chainlit run src/chat_app.py
