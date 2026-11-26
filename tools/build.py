"""Build the bot map database (ootmap/) from your own ROM. Needs only Python 3: no git, no downloads.

  python -I tools/build.py --rom "Zelda no Densetsu - Toki no Ocarina (Japan).z64"

Names, enums, logic and the function index come from the bundled metadata pack (data/meta/);
everything else is read from the ROM you point it at.
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
META = os.path.join(ROOT, "data", "meta")
EXPECTED_MD5 = "9f04c8e68534b870f707c247fa4b50fc"


def run(script, *args, log=None):
    cmd = [sys.executable, "-I", os.path.join(TOOLS, script), TOOLS, *args]
    if log:
        with open(log, "w", encoding="utf-8") as f:
            r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
    else:
        r = subprocess.run(cmd, stdout=subprocess.DEVNULL)
    if r.returncode != 0:
        sys.exit(f"{script} failed" + (f" (see {log})" if log else ""))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rom", required=True, help="path to your Ocarina of Time NTSC-J 1.0 .z64 ROM")
    ap.add_argument("--out", default=os.path.join(ROOT, "ootmap"), help="output folder (default: ootmap/)")
    a = ap.parse_args()

    if not os.path.isfile(a.rom):
        sys.exit(f"ROM not found: {a.rom}")
    with open(a.rom, "rb") as f:
        head = f.read(4)
        f.seek(0)
        md5 = hashlib.md5(f.read()).hexdigest()
    if md5 != EXPECTED_MD5:
        hint = ""
        if head == b"\x37\x80\x40\x12":
            hint = " This looks like a byte-swapped .v64; convert it to .z64 (big-endian) first."
        elif head == b"\x40\x12\x37\x80":
            hint = " This looks like a little-endian .n64; convert it to .z64 (big-endian) first."
        sys.exit(f"ROM MD5 is {md5}, expected {EXPECTED_MD5} (Ocarina of Time NTSC-J 1.0, .z64).{hint}")
    if not os.path.exists(os.path.join(META, "decomp.json")):
        sys.exit("data/meta/ is missing. Re-download the repo, or regenerate it with tools/make_metadata.py.")

    t0 = time.time()
    os.makedirs(a.out, exist_ok=True)
    print("1/3 Reading the ROM (scenes, rooms, actors, exits, collision)...")
    run("extract_map.py", META, os.path.abspath(a.rom), a.out, log=os.path.join(ROOT, "extract.log"))
    print("2/3 Adding the function index...")
    shutil.copytree(os.path.join(META, "code"), os.path.join(a.out, "code"), dirs_exist_ok=True)
    print("3/3 Joining logic, items and warps...")
    run("build_bot_db.py", META, META, a.out)
    src = os.path.join(ROOT, "ootmap")
    if os.path.abspath(a.out) != os.path.abspath(src):
        # custom output folder: bring the hand-written tools and docs along so it works on its own
        for rel in ("query.py", "logic_eval.py", "HOW_TO_USE.md", "BOT_GUIDE.md", os.path.join("logic", "vanilla_settings.json")):
            os.makedirs(os.path.dirname(os.path.join(a.out, rel)), exist_ok=True)
            shutil.copy2(os.path.join(src, rel), os.path.join(a.out, rel))
    print(f"Done in {time.time() - t0:.0f}s. Start with {os.path.join(os.path.abspath(a.out), 'HOW_TO_USE.md')}")


if __name__ == "__main__":
    main()
