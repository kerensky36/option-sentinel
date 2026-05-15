#!/bin/bash
set -e
pip-audit --require-hashes -r requirements.txt
