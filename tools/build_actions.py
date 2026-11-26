"""Write ootmap/actions.json: every player action, every movement option with its physics, rules and speedrun
tech, with animation lengths read from your ROM.

usage: python -I build_actions.py <tools_dir> <data/meta> <rom> <out_dir>
"""
import json
import os
import struct
import sys

sys.path.insert(0, sys.argv[1])
from ootrom import OotRom  # noqa: E402
from headers import load_decomp  # noqa: E402
import movement_sim as S  # noqa: E402
import player_moves as M  # noqa: E402

META, ROM_PATH, OUT = sys.argv[2], sys.argv[3], sys.argv[4]


def jload(name):
    with open(os.path.join(META, name), encoding="utf-8") as f:
        return json.load(f)


def strip_src(o):
    if isinstance(o, dict):
        return {k: _fmt_src(v) if k == "src" else strip_src(v) for k, v in o.items()}
    if isinstance(o, list):
        return [strip_src(x) for x in o]
    return o


def _fmt_src(v):
    items = v if isinstance(v, list) else [v]
    return [dict(file=f, code=c) for f, c in items]


def main():
    D = load_decomp(META)
    R = OotRom(ROM_PATH, D.segments(), 0x7430)
    gk = R.file("gameplay_keep")
    offsets = jload("player_anims.json")
    frames = {name: struct.unpack_from(">h", gk, off)[0] for name, off in offsets.items() if off + 2 <= len(gk)}

    def anim_info(names, groups=()):
        out = {n: frames.get(n) for n in names if n in frames}
        for g in groups:  # GET_PLAYER_ANIM(group, ...) -> the default (unarmed adult) variant
            n = "gPlayerAnim_link_normal_" + g.replace("_link_", "_")
            if n in frames:
                out[n] = frames[n]
        return out

    actions = []
    for a in jload("player_actions.json"):
        a = dict(a)
        a["animation_frames"] = anim_info(a["animations"] + a["setup_animations"],
                                          a["animation_groups"] + a.get("setup_animation_groups", []))
        actions.append(a)

    jumps = []
    for j in M.JUMPS:
        e = strip_src(j)
        if j["velocity_y"] is not None:
            sims = {}
            for gc in M.GRAVITY_CASES:
                r = S.simulate_jump(j["speed_xz"], j["velocity_y"], gc["gravity"])
                sims[gc["case"]] = dict(gravity=gc["gravity"], **r)
            uphill = {}
            for slope in (10, 20, 30):
                r = S.simulate_jump(j["speed_xz"], j["velocity_y"], -1.0, slope)
                uphill[f"{slope}_deg"] = {k: r[k] for k in ("airtime_frames", "distance", "landing_height")}
            e["flat_ground"] = sims
            e["uphill_straight"] = uphill
        e["airborne_speed_units_per_frame"] = S.per_frame(j["speed_xz"])
        e["airborne_speed_units_per_second"] = S.per_second(j["speed_xz"])
        e["animation_frames"] = anim_info(j["landing_anims"] + j["air_anims"])
        if j["velocity_y"] is not None and j["momentum"] == "locked":
            e["chained"] = {"flat": S.jump_chain(j["speed_xz"], j["velocity_y"], -1.0),
                            **{f"{sl}_deg_uphill": S.jump_chain(j["speed_xz"], j["velocity_y"], -1.0, sl) for sl in (10, 20, 30)},
                            "note": "airtime + 1 landing frame per jump with Z held; the landing animation does not block the next jump"}
        jumps.append(e)

    ground = []
    for g in M.GROUND_MOVES:
        e = strip_src(g)
        table = {}
        for b in M.BOOTS:
            cap = b["run_speed_limit"]
            table[b["boots"]] = {f"{s}_deg_uphill": S.ground_target_speed(g["mode"], g["multiplier"], cap, s) for s in (0, 10, 20, 30, 40)}
        e["top_speed_by_boots_and_slope"] = table
        e["top_speed_units_per_frame_flat_adult"] = S.per_frame(S.ground_target_speed(g["mode"], g["multiplier"], 6.0))
        if g["id"] == "roll":
            e["animation_frames"] = anim_info(["gPlayerAnim_link_normal_landing_roll"])
        ground.append(e)

    out = dict(
        about=("Link's actions and movement for bots. Speeds are 'speedXZ' units; world distance per game frame is "
               "speed x 1.5, and NTSC runs 20 game frames per second. verified='code' means read from the decomp; "
               "'community' entries are unverified hints. Animation frame counts come from your ROM."),
        engine=strip_src(M.ENGINE), boots=strip_src(M.BOOTS), speed_formula=strip_src(M.SPEED_FORMULA),
        gravity=strip_src(M.GRAVITY_CASES), ground_moves=ground, jumps=jumps, rules=strip_src(M.RULES),
        speedrun_tech=M.TECH, community_glitches=M.COMMUNITY_GLITCHES,
        player_actions=actions, animation_frames=frames)
    with open(os.path.join(OUT, "actions.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"actions.json: {len(actions)} player actions, {len(jumps)} jumps, {len(ground)} ground moves, {len(frames)} animations")


if __name__ == "__main__":
    main()
