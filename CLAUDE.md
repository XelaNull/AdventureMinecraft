# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build/Test Commands
- Run test suite: `./scripts/test_mod_explorer.sh`
- Download adventure mods: `python ./scripts/download_mods.py`
- Download specific category: `python ./scripts/download_mods.py --category performance-mods`
- Reset download progress: `python ./scripts/download_mods.py --reset`
- Force re-download: `python ./scripts/download_mods.py --force`
- Single mod download: `python ./scripts/mod_explorer.py --download-id <id> --download-source modrinth --mc-version 1.21.5 --loader fabric --output ./server/mods --cache-dir ./scripts/mod_cache`
- Search for mods: `python ./scripts/mod_explorer.py --search "<term>" --source modrinth --mc-version 1.21.5 --loader fabric`
- Start server: `docker-compose up -d`
- Stop server: `docker-compose down`
- Create client pack: `./scripts/create_client_pack.sh`

## Code Style Guidelines
- Python: PEP 8 compliant, docstrings for functions, clear error handling with try/except
- Bash: Use strict error handling, clear variable names, proper quoting
- Naming: snake_case for Python functions/variables, descriptive function names
- Imports: Group standard library, third-party, and local imports
- Error handling: Use proper try/except blocks with specific exceptions
- Logging: Use colorama for colored console output
- Cache management: Support mod caching to prevent unnecessary downloads