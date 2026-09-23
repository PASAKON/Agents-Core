# Jules API Client

The `jules.py` script is a command-line interface for interacting with the Jules API.

## Requirements
- Set `JULES_API_KEY` in `~/.config/mooniex/jules.env` or override the path with the `JULES_ENV_FILE` environment variable.

## Usage

```bash
# Create a session
jules.py create --repo <name> --title <title> --brief <file> [--branch main]

# Get status
jules.py status <id>

# Get diff (last git patch)
jules.py diff <id> [--out f]

# Report activities
jules.py report <id>

# Gate a session (exit 0 if checks pass, 1 otherwise)
jules.py gate <id> --allow <glob> [--allow ...] [--max-bytes 65536]
```
