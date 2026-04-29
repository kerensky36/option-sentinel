# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**option-sentinel** is a Python application for managing options positions (financial derivatives).

## Language & Tooling

This is a Python project. The `.gitignore` includes entries for:
- **uv**, **poetry**, **pdm**, **pipenv** — use whichever package manager is configured once dependencies are added
- **pytest** — test runner
- **ruff** — linter/formatter
- **mypy** / **pytype** / **pyre** — type checkers
- **marimo** / **streamlit** — possible UI frameworks

Once a package manager and dependencies are set up, update this file with the specific commands for install, lint, test, and run.
