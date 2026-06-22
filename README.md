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

Install mpv if needed:

```bash
brew install mpv
```

For offline development, leave `mode: mock` in `config.yaml`. For a live NAS library, set `mode: smb` and fill in the SMB section.

## Run

```bash
uv run python -m lumi
```

### Ubuntu desktop (no terminal)

One-time setup in the project directory:

```bash
chmod +x scripts/lumi-launch.sh scripts/install-desktop-entry.sh
./scripts/install-desktop-entry.sh
```

Then open **Lumi** from the Ubuntu app menu. The launcher uses `.venv/bin/python` and `config.yaml` in this repo.

To remove: `rm ~/.local/share/applications/lumi.desktop`

## Configuration

Copy `config.yaml.example` to `config.yaml` (gitignored). Key settings:

| Setting             | Purpose                                                |
|---------------------|--------------------------------------------------------|
| `mode`              | `mock` or `smb`                                        |
| `library.root_path` | Share path to scan (e.g. `/Movies`)                    |
| `smb.*`             | Host, share, domain, username, password                |
| `cache.posters`     | Poster disk cache directory (empty = platform default) |

Environment overrides:

| Variable            | Purpose                    |
|---------------------|----------------------------|
| `LUMI_CONFIG`       | Path to config file        |
| `LUMI_MODE`         | `mock` or `smb`            |
| `LUMI_SMB_PASSWORD` | SMB password override      |
| `LUMI_LIBRARY_ROOT` | Override library root path |


## Test

```bash
uv run pytest
uv run mypy src/lumi
```
