#!/usr/bin/env python3
import subprocess


def main() -> int:
    subprocess.run(["git", "add", "epg.xml", "epg-run-state.json"], check=True)
    subprocess.run(["git", "config", "user.name", "Actualizador"], check=True)
    subprocess.run(["git", "config", "user.email", "m3u-bot@users.noreply.github.com"], check=True)
    subprocess.run(["git", "commit", "-m", "Actualiza EPG independiente"], check=False)
    return subprocess.run(["git", "push", "origin", "HEAD:main"], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
