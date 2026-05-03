#!/usr/bin/env bash
set -euo pipefail

menu() {
  echo ""
  echo "  [1] Install dependencies"
  echo "  [2] Start dev server"
  echo "  [3] Run CLI query (stub)"
  echo "  [4] Run tests"
  echo "  [5] Open http://localhost:3000"
  echo "  [q] Quit"
  echo ""
  read -rp "Select: " choice
  case "$choice" in
    1) install_deps ;;
    2) dev ;;
    3) cli ;;
    4) run_tests ;;
    5) open_browser ;;
    q|Q) exit 0 ;;
    *) echo "Invalid choice" && sleep 1 && menu ;;
  esac
}

install_deps() {
  echo "Installing..."
  npm install
  uv sync --all-extras
  echo "Done"
  menu
}

dev() {
  echo "Killing existing processes on ports 3000 and 8000..."
  lsof -ti:3000 2>/dev/null | xargs -r kill -9 2>/dev/null || true
  lsof -ti:8000 2>/dev/null | xargs -r kill -9 2>/dev/null || true
  echo "Starting Python API on :8000 and Next.js on :3000..."
  uv run python scripts/dev_server.py &
  npm run dev &
  sleep 3
  open_browser
  echo "Press Ctrl+C to stop both servers."
  wait
}

cli() {
  read -rp "Query: " query
  [ -z "$query" ] && cli && return
  echo "Running..."
  uv run sourcery "$query" --out outputs/cli_run --provider stub
  echo "Done"
  menu
}

run_tests() {
  echo "Running tests..."
  uv run pytest -q
  menu
}

open_browser() {
  local url="http://localhost:3000"
  if command -v xdg-open &>/dev/null; then
    xdg-open "$url"
  elif command -v open &>/dev/null; then
    open "$url"
  else
    echo "Open $url in your browser."
  fi
}

menu
