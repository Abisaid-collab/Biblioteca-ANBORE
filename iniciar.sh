#!/usr/bin/env bash
# Lanzador para macOS/Linux: prepara el entorno la primera vez y abre el chat con el agente.
set -e
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  echo "Preparando el entorno por primera vez, tarda 1 o 2 minutos..."
  python3 -m venv .venv
  .venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt
fi

if [ ! -f .env ]; then
  echo "Falta la clave de Groq. Puedes obtener una gratis en https://console.groq.com/keys"
  read -r -p "Pega tu GROQ_API_KEY y presiona Enter: " CLAVE
  echo "GROQ_API_KEY=$CLAVE" > .env
fi

.venv/bin/python agente.py
