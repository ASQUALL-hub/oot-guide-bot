"""MAINTAINERS ONLY (called by make_metadata.py): evidence for every Player_Action_* function in the decomp,
plus the offsets of Link's animation headers in gameplay_keep, so a ROM-only build can read animation lengths."""
import collections
import os
import re

import player_moves

PLAYER_C = os.path.join("src", "overlays", "actors", "ovl_player_actor", "z_player.c")


def _bodies(src_text, functions):
    lines = src_text.splitlines()
    return {f["name"]: "\n".join(lines[f["line"] - 1:f["end_line"]]) for f in functions}


def _evidence(body):
    return dict(
        animations=sorted(set("gPlayerAnim_link_" + a for a in re.findall(r"gPlayerAnim_link_(\w+)", body))),
        animation_groups=sorted(set(re.findall(r"PLAYER_ANIMGROUP_(\w+)", body))),
        sounds=sorted(set(re.findall(r"NA_SE_((?:PL|VO_LI|IT)_\w+)", body))),
        state_flags=sorted(set(re.findall(r"(PLAYER_STATE[123]_\w+)", body))),
    )


def player_actions(decomp_root, functions):
    """functions: entries from scan_source.py's functions.json."""
    with open(os.path.join(decomp_root, PLAYER_C), encoding="utf-8") as f:
        src = f.read()
    fns = [f for f in functions if f["owner"] == "player_actor"]
    body = _bodies(src, fns)
    by_name = {f["name"]: f for f in fns}
    acts = sorted({n for n in body if n.startswith("Player_Action_")}, key=lambda n: by_name[n]["line"])
    entered = collections.defaultdict(set)
    for n, b in body.items():
        for a in set(re.findall(r"Player_Action_\w+", b)):
            if a != n:
                entered[a].add(n)
    out = []
    for a in acts:
        label, category, conf = player_moves.ACTION_LABELS.get(a, (None, None, None))
        setups = sorted(entered[a])
        setup_anims = sorted({x for s in setups for x in _evidence(body[s])["animations"]})
        setup_groups = sorted({x for s in setups for x in _evidence(body[s])["animation_groups"]})
        out.append(dict(function=a, file=PLAYER_C.replace(os.sep, "/"), line=by_name[a]["line"],
                        label=label, category=category, label_confidence=conf,
                        decomp_named=not re.match(r"Player_Action_[0-9A-F]{8}$", a),
                        entered_from=setups, setup_animations=setup_anims, setup_animation_groups=setup_groups,
                        **_evidence(body[a])))
    missing = [a["function"] for a in out if not a["label"]]
    assert not missing, f"add labels to player_moves.ACTION_LABELS for: {missing}"
    return out


def player_anim_offsets(decomp_root, version="ntsc-1.0"):
    with open(os.path.join(decomp_root, "assets", "xml", "objects", "gameplay_keep.xml"), encoding="utf-8") as f:
        xml = f.read()

    def keep_block(m):
        return m.group(2) if re.fullmatch(m.group(1), version) else ""
    xml = re.sub(r'<Version Pattern="([^"]+)">(.*?)</Version>', keep_block, xml, flags=re.S)
    return {m.group(1): int(m.group(2), 16)
            for m in re.finditer(r'<PlayerAnimation Name="(\w+)" Offset="(0x[0-9A-Fa-f]+)"', xml)}


def verify_sources(decomp_root):
    """Every `src` snippet in player_moves.py must still appear verbatim in the decomp."""
    srcs = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "src":
                    srcs.extend(v if isinstance(v, list) else [v])
                else:
                    walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk([player_moves.ENGINE, player_moves.BOOTS, player_moves.SPEED_FORMULA, player_moves.JUMPS,
          player_moves.GRAVITY_CASES, player_moves.GROUND_MOVES, player_moves.RULES, player_moves.BODY,
          player_moves.ATTACKS, player_moves.COLLISION_ENGINE, player_moves.TICK])
    cache, bad = {}, []
    for f, snip in srcs:
        if f not in cache:
            with open(os.path.join(decomp_root, f), encoding="utf-8") as fh:
                cache[f] = fh.read()
        if snip not in cache[f]:
            bad.append((f, snip))
    assert not bad, f"player_moves.py cites code that is no longer in the decomp: {bad}"
    return len(srcs)
