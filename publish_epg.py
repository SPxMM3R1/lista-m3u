#!/usr/bin/env python3
import subprocess


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=False)


def push_with_rebase() -> int:
    first_push = run("git", "push", "origin", "HEAD:main")
    if first_push.returncode == 0:
        return 0

    # El proceso de canales puede publicar un commit mientras la EPG se
    # construye. La EPG solo toca sus propios archivos, por lo que se puede
    # rebasar de forma segura sobre el main nuevo y reintentar sin mezclar
    # historiales ni perder el commit del otro proceso.
    fetched = run("git", "fetch", "origin", "main")
    if fetched.returncode != 0:
        return first_push.returncode
    rebased = run("git", "rebase", "origin/main")
    if rebased.returncode != 0:
        return rebased.returncode
    return run("git", "push", "origin", "HEAD:main").returncode


def main() -> int:
    subprocess.run(
        ["git", "add", "epg.xml", "3.m3u", "epg-run-state.json"],
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "Actualizador"], check=True)
    subprocess.run(["git", "config", "user.email", "m3u-bot@users.noreply.github.com"], check=True)
    subprocess.run(["git", "commit", "-m", "Actualiza EPG independiente [skip ci]"], check=False)
    return push_with_rebase()


if __name__ == "__main__":
    raise SystemExit(main())
