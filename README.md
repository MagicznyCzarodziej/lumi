# Lumi

Browse an SMB-hosted video library, classify films/series, and play media via an external player.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- External video player (default: `mpv`)

## Setup

```bash
uv sync
cp config.yaml.example config.yaml
```

For offline development, leave `mode: mock` in `config.yaml`. For a live NAS library, set `mode: smb` and fill in the SMB section (see below).

## Run

```bash
# Mock library (bundled JSON fixture, no network)
LUMI_MODE=mock uv run python -m lumi

# Or rely on config.yaml
uv run python -m lumi
```

## Configuration

Copy `config.yaml.example` to `config.yaml` (gitignored). Key settings:

| Setting | Purpose |
|---------|---------|
| `mode` | `mock` or `smb` |
| `library.root_path` | Share path to scan (e.g. `/Movies`) |
| `smb.*` | Host, share, domain, username, password |
| `player.command` | External player argv; `{path}` / `{smb_uri}` expand to an `smb://` streaming URL |
| `cache.posters` | Poster disk cache directory (empty = platform default) |

Environment overrides:

| Variable | Purpose |
|----------|---------|
| `LUMI_CONFIG` | Path to config file |
| `LUMI_MODE` | `mock` or `smb` |
| `LUMI_SMB_PASSWORD` | SMB password override |
| `LUMI_LIBRARY_ROOT` | Override library root path |

**Video playback streams over SMB** — Lumi passes an `smb://user:pass@host/share/path` URI to the external player. Video files are **never** copied to local disk.

Poster images are read over SMB into memory and cached on disk under `~/Library/Caches/lumi/posters` (macOS) or the platform equivalent.

Install mpv if needed:

```bash
brew install mpv
```

## Test

```bash
uv run pytest
uv run mypy src/lumi
```
