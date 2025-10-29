#! /bin/bash

export CHAINLIT_HOST=0.0.0.0
export CHAINLIT_PORT=8080

UV_CHECK=$(which uv)

if [ -z "${UV_CHECK}" ]; then

        curl -LsSf https://astral.sh/uv/install.sh | sh

        if [ "$?" -eq 0 ]; then
                echo "uv installed."
                . "${HOME}/.local/bin/env"
        fi
fi

uv sync
uv run chainlit run src/chat_app.py