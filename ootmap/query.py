"""Query the OoT map database. Needs only Python 3 and the JSON files next to this script.

  python query.py find "piece of heart"         items whose name/item matches
  python query.py scene "kokiri forest"         exits, grottos, doors and items in a scene
  python query.py route "links house" "deku tree" [--age child|adult]
                                                  shortest chain of loading zones between two scenes
  python query.py entrance ENTR_LOST_WOODS_9    where an entrance index puts you
  python query.py region "KF Links House"       logic region: locations, exits and their rules
  python query.py func EnBox_Init               a decomp function: file, line, signature, callees
  python query.py warps                          warp songs, blue warps, owls, grottos
Add --json to any command for machine-readable output.
"""
import json
import os
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
_cache = {}


def load(rel):
    if rel not in _cache:
        with open(os.path.join(HERE, rel), encoding="utf-8") as f:
            _cache[rel] = json.load(f)
    return _cache[rel]


def norm(s):
    return "".join(c for c in str(s).lower() if c.isalnum())


def scene_lookup(q):
    idx = load("scenes/_index.json")
    try:
        sid = int(q, 0)
        return next(r for r in idx if r["scene_id"] == sid)
    except (ValueError, StopIteration):
        pass
    nq = norm(q)
    for key in ("enum", "name", "file"):
        for r in idx:
            if norm(r.get(key) or "") == nq or norm(r.get(key) or "") == "scene" + nq:
                return r
    for r in idx:
        if nq in norm(r.get("name") or "") or nq in norm(r.get("enum") or ""):
            return r
    raise SystemExit(f"no scene matches {q!r}")


def cmd_find(q):
    nq = norm(q)
    out = []
    for it in load("items.json"):
        hay = norm(it["name"]) + norm(it.get("vanilla_item") or "")
        for a in it.get("rom_actors") or []:
            hay += norm((a.get("decoded") or {}).get("get_item") or "")
        if nq in hay:
            out.append(it)
    return out


def summarize_item(it):
    lines = [f"{it['name']}  [{it['type']}]  vanilla: {it.get('vanilla_item')}"]
    lines.append(f"  scene: {it.get('scene_name') or it.get('scene_enum')}   logic region: {it.get('region')}")
    for a in (it.get("rom_actors") or [])[:3]:
        d = a.get("decoded") or {}
        lines.append(f"  at room {a['room']} pos {a['pos']} layers {a.get('layers')} actor {a['actor']} {d.get('get_item') or d.get('drop') or ''}")
    if it.get("rom_note"):
        lines.append(f"  note: {it['rom_note']}")
    lines.append(f"  how: {it.get('how_obtained')}")
    lines.append(f"  requires (randomizer logic, vanilla settings): {it.get('logic_rule')}")
    return "\n".join(lines)


def cmd_scene(q):
    row = scene_lookup(q)
    sg = next(n for n in load("scene_graph.json") if n["scene_id"] == row["scene_id"])
    items = [i for i in load("items.json") if i.get("scene_id") == row["scene_id"]]
    return dict(scene=row, edges=sg["edges"], room_links=sg["room_links"], items=items)


def cmd_route(a, b, age=None):
    src, dst = scene_lookup(a)["scene_id"], scene_lookup(b)["scene_id"]
    graph = {n["scene_id"]: n for n in load("scene_graph.json")}
    layers_ok = None
    if age == "child":
        layers_ok = {"child_day", "child_night"}
    elif age == "adult":
        layers_ok = {"adult_day", "adult_night"}
    prev = {src: None}
    dq = deque([src])
    while dq:
        s = dq.popleft()
        if s == dst:
            break
        for e in graph.get(s, {}).get("edges", []):
            t = e.get("to_scene")
            if t is None or t in prev or e["via"] == "exit_list":
                continue
            if layers_ok and not (set(e.get("layers", [])) & layers_ok):
                continue
            prev[t] = (s, e)
            dq.append(t)
    if dst not in prev:
        return dict(found=False, note="no loading-zone path in the scene graph (may need a warp, or check the age filter)")
    steps, cur = [], dst
    while prev[cur]:
        s, e = prev[cur]
        steps.append(dict(from_scene=graph[s]["enum"], via=e["via"], go_to=e.get("at"), exit_index=e.get("exit_index"),
                          entrance=e.get("entrance_enum"), arrive_scene=e.get("to_scene_enum"), arrive_at=e.get("arrive_at"),
                          requires=e.get("requires")))
        cur = s
    return dict(found=True, steps=list(reversed(steps)),
                note="positions are in game units (x, y, z; y is up). Logic requirements for each hop are in logic/world_graph.json")


def cmd_entrance(q):
    ents = load("entrances.json")
    try:
        i = int(q, 0)
        return ents[i]
    except ValueError:
        return next((e for e in ents if e["enum"] == q), None)


def cmd_region(q):
    regs = load("logic/world_graph.json")["regions"]
    nq = norm(q)
    return [r for r in regs if norm(r["region"]) == nq] or [r for r in regs if nq in norm(r["region"])]


def cmd_func(q):
    fs = load("code/functions.json")
    return [f for f in fs if f["name"] == q] or [f for f in fs if q.lower() in f["name"].lower()][:25]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_json = "--json" in sys.argv
    age = None
    for a in sys.argv:
        if a.startswith("--age="):
            age = a.split("=", 1)[1]
    if "--age" in sys.argv:
        age = sys.argv[sys.argv.index("--age") + 1]
        args = [a for a in args if a != age]
    if not args:
        print(__doc__)
        return
    c, rest = args[0], args[1:]
    if c == "find":
        res = cmd_find(" ".join(rest))
        if not as_json:
            print("\n\n".join(summarize_item(i) for i in res) or "nothing found")
            return
    elif c == "scene":
        res = cmd_scene(" ".join(rest))
        if not as_json:
            s = res["scene"]
            print(f"{s['name']} ({s['enum']}, id {s['scene_id']:#04x}, {s['rooms']} rooms)")
            print("exits:")
            for e in res["edges"]:
                print(f"  [{e['via']}] at {e.get('at')} -> {e.get('to_scene_enum')} spawn {e.get('to_spawn')} ({e.get('entrance_enum')})"
                      f"{'  requires ' + e['requires'] if e.get('requires') else ''}  layers {e.get('layers')}")
            print("doors / room links:")
            for t in res["room_links"]:
                d = t.get("decoded") or {}
                print(f"  {t['actor']} at {t['pos']} rooms {t['rooms']} {d.get('door_type', '')} {d.get('requires', '')}")
            print("items:")
            for i in res["items"]:
                print("  " + summarize_item(i).replace("\n", "\n  "))
            return
    elif c == "route":
        res = cmd_route(rest[0], rest[1], age)
        if not as_json:
            if not res["found"]:
                print(res["note"])
                return
            for k, s in enumerate(res["steps"], 1):
                print(f"{k}. in {s['from_scene']}: go to {s['go_to']} ({s['via']}{', requires ' + s['requires'] if s.get('requires') else ''})"
                      f" -> arrive {s['arrive_scene']} at {(s['arrive_at'] or {}).get('pos')}")
            return
    elif c == "entrance":
        res = cmd_entrance(rest[0])
    elif c == "region":
        res = cmd_region(" ".join(rest))
    elif c == "func":
        res = cmd_func(rest[0])
    elif c == "warps":
        res = load("warps.json")
    else:
        print(__doc__)
        return
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
