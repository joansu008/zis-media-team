# Cross-platform operation

Committed code uses `pathlib` and project-relative defaults. Local absolute paths are supplied through environment variables and never committed.

## macOS to Windows

1. Clone the repository.
2. Install Python 3.9+ and Git.
3. Optionally install FFmpeg and make it available on `PATH`.
4. Keep `ZIS_EXECUTION_MODE=codex_native` for signed-in Codex execution. Only API mode needs `ZIS_MODEL_PROVIDER`, per-agent model names, and a local provider credential. Configure video adapter values per machine when needed.
5. Run `python -m src.cli capabilities` and the test suite.

One concrete task stays on one computer from start to finish. Git synchronizes definitions, rules, workflows, registries, source, tests, and docs—not active task workspaces, media, caches, exports, binaries, `.env`, or credentials.

The dependency-free runtime loads simple `KEY=VALUE` entries from a local `.env` and gives already-exported shell values precedence. `.env` is ignored by Git.
