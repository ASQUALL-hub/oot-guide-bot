"""MAINTAINERS ONLY: regenerate the metadata pack (data/meta/) from the reference checkouts.

Users never need this: data/meta/ ships with the repo, so a build only needs the ROM.
Run it after bumping the pinned decomp / randomizer commits:

  python -I tools/fetch_refs.py
  python -I tools/make_metadata.py

The pack holds names, enums and layouts (from zeldaret/oot), the randomizer's logic (MIT, from
OoT-Randomizer) and the decomp function index. It contains no data read from the ROM.
"""
import json
import os
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from headers import Decomp  # noqa: E402
import decode  # noqa: E402
import ootr_data  # noqa: E402
from fetch_refs import REFS  # noqa: E402

REF = os.path.join(ROOT, "ref")
META = os.path.join(ROOT, "data", "meta")


def dump(obj, *parts, indent=None):
    p = os.path.join(META, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent, separators=None if indent else (",", ":"))
    return p


def main():
    D = Decomp(os.path.join(REF, "oot"))
    enums = {}
    for actor, name in decode.ACTOR_ENUMS:
        enums[f"{actor}:{name}"] = D.actor_enum(actor, name)
        assert enums[f"{actor}:{name}"], f"enum {name} not found for {actor}"
    for actor, prefix, stop in decode.ACTOR_PREFIXED:
        enums[f"{actor}:{prefix}*"] = D.actor_prefixed(actor, prefix, stop)
    decomp = dict(
        segments=D.segments("ntsc-1.0"), scenes=D.scenes, entrances=D.entrances, actors=D.actors, objects=D.objects,
        item_ids=D.item_ids, gi_ids=D.gi_ids, item00=D.item00, floor_types=D.floor_types, wall_types=D.wall_types,
        floor_props=D.floor_props, materials=D.materials, floor_effects=D.floor_effects,
        actor_descriptions={a["name"]: D.actor_description(a["name"]) for a in D.actors.values() if a["name"]},
        get_item_table=D.get_item_table(), warp_song_entrances=D.warp_song_entrances(),
        grotto_entrances=D.grotto_entrances(), actor_enums=enums)
    print("wrote", dump(decomp, "decomp.json"))
    print("wrote", dump(ootr_data.load_source(os.path.join(REF, "ootr")), "ootr.json"))
    subprocess.run([sys.executable, "-I", os.path.join(TOOLS, "scan_source.py"), TOOLS, os.path.join(REF, "oot"),
                    os.path.join(META, "code")], check=True)
    manifest = dict(
        note="Reference metadata only (names, enums, layouts, randomizer logic, function index). No ROM data.",
        rom=dict(name="Ocarina of Time NTSC-J 1.0", md5="9f04c8e68534b870f707c247fa4b50fc"),
        sources={r["dir"]: dict(url=r["url"], commit=r["commit"]) for r in REFS})
    print("wrote", dump(manifest, "manifest.json", indent=1))


if __name__ == "__main__":
    main()
