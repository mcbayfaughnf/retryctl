# retryctl

A CLI wrapper that adds configurable retry logic with backoff strategies to any shell command or script.

---

## Installation

```bash
pip install retryctl
```

Or install from source:

```bash
git clone https://github.com/yourname/retryctl.git && cd retryctl && pip install .
```

---

## Usage

```bash
retryctl [OPTIONS] -- <command>
```

### Examples

```bash
# Retry a failing curl command up to 5 times with exponential backoff
retryctl --attempts 5 --backoff exponential -- curl https://example.com/api

# Retry a script with a fixed 2-second delay between attempts
retryctl --attempts 3 --backoff fixed --delay 2 -- ./deploy.sh

# Retry with a maximum backoff cap of 30 seconds
retryctl --attempts 10 --backoff exponential --max-delay 30 -- python sync.py
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--attempts` | `3` | Maximum number of retry attempts |
| `--backoff` | `fixed` | Backoff strategy: `fixed`, `exponential`, or `linear` |
| `--delay` | `1` | Initial delay in seconds between retries |
| `--max-delay` | `60` | Maximum delay cap in seconds |
| `--on-exit-code` | any non-zero | Only retry on specific exit codes |

---

## Backoff Strategies

- **fixed** — waits the same amount of time between every attempt
- **linear** — increases the delay linearly with each attempt
- **exponential** — doubles the delay after each failed attempt

---

## License

MIT © 2024 [yourname](https://github.com/yourname)