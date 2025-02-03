#!/usr/bin/env bash

export PYTHON_PREFIX=~/miniforge
${PYTHON_PREFIX}/bin/streamlit run ../run.py --server.enableCORS=false --server.enableXsrfProtection=false --server.port 8080
