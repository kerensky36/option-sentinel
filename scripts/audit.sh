#!/bin/bash
set -e
# Audit pinned dependencies for known vulnerabilities (specs/022 FR-510).
pip-audit -r requirements.txt
