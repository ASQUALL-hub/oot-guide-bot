"""MAINTAINERS ONLY: fetch the two reference projects into ref/ at the pinned commits.

  python -I tools/fetch_refs.py

Only needed to regenerate data/meta/ with make_metadata.py. Normal builds don't use it.
"""
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = [
    dict(dir="oot", url="https://github.com/zeldaret/oot.git", commit="2c78bc78fd7db383c5f81a83a5169e8de9eb3a0d"),
    dict(dir="ootr", url="https://github.com/OoTRandomizer/OoT-Randomizer.git", commit="d262f7a506d8059e538a899ae0dd7d18d3987a6f"),
]


def git(d, *args, check=True):
    return subprocess.run(["git", "-C", d, *args], check=check, capture_output=True, text=True)


def main():
    for r in REFS:
        d = os.path.join(ROOT, "ref", r["dir"])
        if not os.path.isdir(os.path.join(d, ".git")):
            os.makedirs(d, exist_ok=True)
            git(d, "init", "-q")
            git(d, "config", "core.longpaths", "true")
            git(d, "remote", "add", "origin", r["url"])
        head = git(d, "rev-parse", "--verify", "-q", "HEAD", check=False).stdout.strip()
        if head != r["commit"]:
            print(f"fetching {r['url']} @ {r['commit'][:10]}")
            git(d, "fetch", "-q", "--depth", "1", "origin", r["commit"])
            git(d, "checkout", "-q", "-f", r["commit"])
        print(f"{r['dir']}: {r['commit'][:10]}")


if __name__ == "__main__":
    main()
