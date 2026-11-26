"""Join the ROM extraction (ootmap/) with OoT Randomizer logic data into bot-facing tables.

Reads the randomizer repo as data only (ast/json, never imported or executed).
usage: python -I build_bot_db.py <tools_dir> <decomp_root | data/meta> <ootr_root | data/meta> <ootmap_dir>
"""
import sys
import os
import json
from collections import defaultdict

sys.path.insert(0, sys.argv[1])
from headers import load_decomp  # noqa: E402
import ootr_data  # noqa: E402

DECOMP, OOTR, OUT = sys.argv[2], sys.argv[3], sys.argv[4]
D = load_decomp(DECOMP)


def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def jdump(obj, *parts, compact=False):
    p = os.path.join(OUT, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        if compact:
            json.dump(obj, f, separators=(",", ":"), ensure_ascii=False)
        else:
            json.dump(obj, f, indent=1, ensure_ascii=False)


# ------------------------------------------------------------------ load ROM map
index = jload(os.path.join(OUT, "scenes", "_index.json"))
scenes = {}
for row in index:
    scenes[row["scene_id"]] = jload(os.path.join(OUT, row["scene_json"]))
entrances = jload(os.path.join(OUT, "entrances.json"))
OOTR_DATA = ootr_data.load(OOTR)  # randomizer checkout, or the bundled metadata pack (data/meta)
scene_names = OOTR_DATA["scene_names"]

# ------------------------------------------------------------------ load logic
locs = OOTR_DATA["locations"]
regions = OOTR_DATA["regions"]
helpers = OOTR_DATA["helpers"]
shuffle_table = OOTR_DATA["shuffle_table"]

loc_region = {}
for r in regions:
    for ln, rule in r.get("locations", {}).items():
        loc_region[ln] = (r["region_name"], rule.strip())

# ------------------------------------------------------------------ actor indexes
by_scene_kind = defaultdict(list)   # (scene, kind) -> [ref]
for sid, sc in scenes.items():
    for room in sc["rooms"]:
        for label, L in room["layers"].items():
            if L["header_source"] != "own" and label != "child_day":
                continue
            for a in L["actors"]:
                dec = a.get("decoded")
                if dec:
                    ref = dict(scene=sid, room=room["room"], layer=label, actor_index=a["index"], actor=a["actor"],
                               pos=a["pos"], params=a["params"], decoded=dec)
                    by_scene_kind[(sid, dec["kind"])].append(ref)
                    if isinstance(dec.get("contains"), dict) and dec["contains"].get("kind"):
                        by_scene_kind[(sid, dec["contains"]["kind"])].append(dict(ref, decoded=dict(dec["contains"], spawner=dec["kind"])))


def dedupe(refs):
    seen, out = {}, []
    for r in refs:
        k = (r["scene"], r["room"], r["actor_index"], r["params"], tuple(r["pos"]))
        if k in seen:
            seen[k]["layers"].append(r["layer"])
            continue
        r = dict(r)
        r["layers"] = [r.pop("layer")]
        seen[k] = r
        out.append(r)
    return out


def actor_at(sid, room, layer_idx, idx):
    sc = scenes.get(sid)
    if not sc or room >= len(sc["rooms"]):
        return None
    labels = [L["label"] for L in sc["layers"]]
    if layer_idx >= len(labels):
        return None
    L = sc["rooms"][room]["layers"].get(labels[layer_idx])
    if not L or idx >= len(L["actors"]) or idx < 0:
        return None
    a = L["actors"][idx]
    return dict(scene=sid, room=room, layers=[labels[layer_idx]], actor_index=idx, actor=a["actor"], pos=a["pos"],
                params=a["params"], decoded=a.get("decoded"))


# grotto holes: (scene, return byte) -> Door_Ana ref ; generic grotto chests live in scene 0x3E
grotto_holes = {}
for (sid, kind), refs in by_scene_kind.items():
    if kind == "grotto":
        for r in dedupe(refs):
            grotto_holes[(sid, int(r["params"], 16) & 0xFF)] = r

XFLAG_TYPES = {"Freestanding", "Pot", "Crate", "SmallCrate", "FlyingPot", "Beehive", "RupeeTower", "Wonderitem", "SilverRupee"}
XFLAG_EXPECT = {"Freestanding": {"collectible", "special_item", "heart_container", None}, "Pot": {"pot"}, "FlyingPot": {None},
                "Crate": {"large_crate"}, "SmallCrate": {"small_crate"}, "Beehive": {"beehive"},
                "Wonderitem": {"hidden_item_trigger"}, "SilverRupee": {"silver_rupee_system"}, "RupeeTower": {None}}


def xflag_match(sid, default, typ):
    if isinstance(default, list):
        default = default[0]
    room, setup, flag = default[:3]
    # Verified against the ROM: the randomizer numbers room actors from 1, so actor_index = flag - 1.
    # In the shared grotto scene (0x3E) its "setup" slot holds a grotto id, not a scene layer.
    if sid == 0x3E:
        setup = 0
    a = actor_at(sid, room, setup, flag - 1)
    if not a:
        return None
    k = (a.get("decoded") or {}).get("kind")
    return (k in XFLAG_EXPECT.get(typ, set()), -1, a)


xflag_offset_votes = defaultdict(int)
for name, (typ, scene, default, addrs, vanilla, tags) in locs.items():
    if typ in XFLAG_TYPES and scene is not None and default is not None and scene in scenes:
        m = xflag_match(scene, default, typ)
        if m and m[0]:
            xflag_offset_votes[m[1]] += 1

# ------------------------------------------------------------------ build items
RUNTIME_NOTES = {
    "_default": "not placed in the room's actor list: another actor spawns it at runtime (NPC, minigame, enemy drop, spinning pot...). Use region + logic_rule + how_obtained.",
    "Shop": "shelf items are spawned by the shopkeeper actor (En_Ossan) from its own inventory table, not placed in the room",
    "BossHeart": "the heart container is spawned by the boss when it dies",
    "Chest": "this chest is spawned at runtime (e.g. Treasure Chest Shop minigame), not placed in the room",
    "GS Token": "this Gold Skulltula is not in the room's actor list or its spawner was not decoded; use region + logic_rule",
}
# actors (verified in the decomp source) that spawn item sources at runtime
SPAWNERS = {
    "Chest": {"Bg_Mori_Hineri": "the twisting-corridor actor spawns this chest once the hallway is straightened",
              "En_Changer": "the Treasure Chest Shop minigame spawns these chests"},
    "Collectable": {"Bg_Spot18_Basket": "Goron City spinning pot (drop a bomb in it)",
                    "En_Tk": "Dampé's gravedigging tour (dig spot)",
                    "En_Po_Relay": "Dampé's ghost race reward",
                    "En_GeldB": "a Gerudo guard drops this key when defeated",
                    "Bg_Haka_Tubo": "the giant spinning skull pot drops this small key when you get a bomb into it"},
    "BossHeart": {n: "the boss spawns its heart container when defeated" for n in
                  ("Boss_Goma", "Boss_Dodongo", "Boss_Va", "Boss_Ganondrof", "Boss_Fd", "Boss_Fd2", "Boss_Mo", "Boss_Sst", "Boss_Tw")},
    "Shop": {"En_Ossan": "the shopkeeper spawns the shelf items from its own inventory table"},
}
by_scene_actor = defaultdict(list)
for sid, sc in scenes.items():
    for room in sc["rooms"]:
        for label, L in room["layers"].items():
            if L["header_source"] != "own" and label != "child_day":
                continue
            for a in L["actors"]:
                by_scene_actor[(sid, a["actor"])].append(dict(scene=sid, room=room["room"], layer=label, actor_index=a["index"],
                                                             actor=a["actor"], pos=a["pos"], params=a["params"], decoded=a.get("decoded")))


def spawner_refs(sid, typ):
    out = []
    for name, note in SPAWNERS.get(typ, {}).items():
        for r in dedupe(by_scene_actor.get((sid, name), [])):
            out.append(dict(r, spawns_note=note))
    return out


items = []
unmatched = defaultdict(int)
for name, (typ, scene, default, addrs, vanilla, tags) in locs.items():
    if tags and any("Master Quest" == t for t in tags) and name not in loc_region:
        continue
    if " MQ " in f" {name} " and name not in loc_region:
        continue
    region, rule = loc_region.get(name, (None, None))
    if region is None and typ not in ("Event",):
        # location only exists in MQ / non-vanilla variants
        continue
    rec = dict(name=name, type=typ, vanilla_item=vanilla, region=region, logic_rule=rule,
               tags=list(tags) if tags else [], scene_id=scene if isinstance(scene, int) and scene != 0xFF else None)
    if rec["scene_id"] is not None:
        rec["scene_enum"] = D.scenes.get(scene, {}).get("enum")
        rec["scene_name"] = scene_names.get(scene)
    rom = None
    how = None
    if typ == "Chest" and scene in scenes:
        cands = [r for r in dedupe(by_scene_kind[(scene, "chest")]) if r["decoded"]["treasure_flag"] == default]
        if scene == 0x3E and not cands:
            # generic grotto chest: contents come from the overworld grotto hole
            holes = [h for (s, rb), h in grotto_holes.items() if (rb & 0x1F) == default and h["decoded"].get("dest_scene") == 0x3E]
            cands = holes
            how = "generic grotto chest spawned by En_Torch; contents/flag come from the Door_Ana you entered through"
        rom = cands
        how = how or "open the chest (treasure flag %#x)" % default
    elif typ in ("Collectable",) and scene in scenes:
        rom = [r for k in ("collectible", "special_item") for r in dedupe(by_scene_kind[(scene, k)])
               if r["decoded"].get("collectible_flag") == default or r["decoded"].get("treasure_flag") == default]
        how = "pick up the freestanding item (collectible flag %#x)" % default
    elif typ == "BossHeart" and scene in scenes:
        rom = dedupe(by_scene_kind[(scene, "heart_container")])
        how = "appears after the boss is defeated"
    elif typ == "GS Token":
        rom = []
        for (sid, kind), refs in by_scene_kind.items():
            if kind == "gold_skulltula":
                for r in dedupe(refs):
                    if r["decoded"]["gs_flag_index"] == scene and int(r["decoded"]["gs_bit_mask"], 16) == default:
                        rom.append(r)
        how = "kill the Gold Skulltula and collect its token (GS flags byte %#x, bit %#x)" % (scene, default)
        rec["scene_id"] = None
        rec.pop("scene_enum", None)
        rec.pop("scene_name", None)
        rec["gs_flags"] = dict(byte=scene, mask=default)
        if rom:
            rec["scene_id"] = rom[0]["scene"]
            rec["scene_enum"] = D.scenes.get(rom[0]["scene"], {}).get("enum")
            rec["scene_name"] = scene_names.get(rom[0]["scene"])
    elif typ in XFLAG_TYPES and scene in scenes and default is not None:
        m = xflag_match(scene, default, typ)
        rom = [m[2]] if m else []
        how = {"Pot": "break the pot", "FlyingPot": "break the flying pot", "Crate": "break the crate", "SmallCrate": "break the small crate",
               "Beehive": "break the beehive", "Freestanding": "pick up the item", "RupeeTower": "collect the rupee circle/tower",
               "Wonderitem": "trigger the hidden item spot", "SilverRupee": "collect the silver rupee"}.get(typ)
        rec["xflag"] = dict(room=default[0] if not isinstance(default, list) else default[0][0],
                            layer=(default[1] if not isinstance(default, list) else default[0][1]),
                            actor_number=(default[2] if not isinstance(default, list) else default[0][2]))
    elif typ in ("Scrub", "GrottoScrub") and scene in scenes:
        rom = dedupe(by_scene_kind[(scene, "business_scrub")])
        how = "buy from the Business Scrub (hit it with a nut/shield-reflect, then talk)"
    elif typ == "Shop" and scene in scenes:
        rom = dedupe(by_scene_kind[(scene, "shop_item")])
        how = "buy from the shop"
    elif typ in ("NPC", "Song", "Cutscene", "Boss", "MaskShop"):
        how = {"NPC": "reward from an NPC/minigame (see logic_rule for requirements)", "Song": "taught in a cutscene",
               "Cutscene": "given in a cutscene", "Boss": "defeat the boss / dungeon reward", "MaskShop": "Happy Mask Shop"}[typ]
    rec["how_obtained"] = how
    if rom is not None:
        rec["rom_actors"] = rom
        if not rom:
            sp = spawner_refs(scene, typ)
            if sp:
                rec["rom_actors"] = sp
                rec["rom_note"] = "spawned at runtime by the actor listed in rom_actors: " + sp[0]["spawns_note"]
            else:
                unmatched[typ] += 1
                rec["rom_note"] = RUNTIME_NOTES.get(typ, RUNTIME_NOTES["_default"])
    items.append(rec)

# ------------------------------------------------------------------ world graph
shuffle_by_name = {}
for row in shuffle_table:
    cat = row[0]
    for pair in row[1:]:
        nm, data = pair
        shuffle_by_name[nm] = dict(category=cat, **data)

exit_lookup = defaultdict(list)  # entrance base index -> [(scene, exit)]
for sid, sc in scenes.items():
    for L in sc["layers"][:4]:
        for e in L["exits"]:
            if e.get("loading_zone"):
                exit_lookup[e["entrance"]].append(dict(scene=sid, scene_enum=sc["enum"], layer=L["label"],
                                                       exit_index=e["exit_index"], loading_zone=e["loading_zone"]))


def spawn_point(entr_idx):
    if not (0 <= entr_idx < len(entrances)):
        return None
    e = entrances[entr_idx]
    sc = scenes.get(e["scene"])
    if not sc:
        return None
    L = sc["layers"][0]
    sp = next((s for s in L["spawns"] if s["spawn"] == e["spawn"]), None)
    if not sp:
        return None
    pe = next((p for p in L["player_entries"] if p["index"] == sp["player_entry"]), None)
    return dict(scene=e["scene"], scene_enum=sc["enum"], room=sp["room"], pos=pe["pos"] if pe else None,
                facing_deg=pe["rot_y_deg"] if pe else None)


graph_regions = []
for r in regions:
    exits = []
    for to, rule in r.get("exits", {}).items():
        ex = dict(to=to, rule=rule.strip())
        sh = shuffle_by_name.get(f"{r['region_name']} -> {to}")
        if sh:
            ex["category"] = sh["category"]
            idx = sh.get("index")
            if sh.get("grotto_id") is not None:
                ex["grotto"] = dict(grotto_id=sh["grotto_id"], entrance=sh.get("entrance"), content_byte=sh.get("content"), scene=sh.get("scene"))
                idx = sh.get("entrance", idx)
                hole = grotto_holes.get((sh.get("scene"), sh.get("content")))
                if hole:
                    ex["grotto"]["hole_position"] = hole["pos"]
                    ex["grotto"]["hole_room"] = hole["room"]
                    ex["grotto"]["requires_to_open"] = hole["decoded"].get("requires")
            if idx is not None:
                ex["entrance"] = idx
                ex["entrance_enum"] = entrances[idx]["enum"] if idx < len(entrances) else None
                ex["arrive_at"] = spawn_point(idx)
                lz = exit_lookup.get(idx)
                if lz:
                    ex["loading_zones"] = lz
            if sh.get("savewarp_fallback") is not None:
                ex["savewarp_fallback"] = sh["savewarp_fallback"]
        exits.append(ex)
    graph_regions.append(dict(
        region=r["region_name"], scene=r.get("scene"), dungeon=r.get("dungeon"), hint=r.get("hint"),
        is_boss_room=r.get("is_boss_room", False), time_passes=r.get("time_passes", False),
        savewarp=r.get("savewarp"), source_file=r["_file"],
        events={k: v.strip() for k, v in r.get("events", {}).items()},
        locations={k: v.strip() for k, v in r.get("locations", {}).items()},
        exits=exits))

# ------------------------------------------------------------------ ROM scene graph (logic-free)
scene_graph = []
for sid, sc in sorted(scenes.items()):
    node = dict(scene_id=sid, enum=sc["enum"], name=scene_names.get(sid), rooms=sc["room_count"], edges=[], room_links=[])
    for L in sc["layers"]:
        for e in L["exits"]:
            if not e.get("valid", True):
                continue
            node["edges"].append(dict(layer=L["label"], via="loading_zone" if e.get("loading_zone") else "exit_list",
                                      exit_index=e["exit_index"], entrance=e["entrance"], entrance_enum=e.get("entrance_enum"),
                                      to_scene=e.get("dest_scene"), to_scene_enum=e.get("dest_scene_enum"), to_spawn=e.get("dest_spawn"),
                                      at=(e.get("loading_zone") or {}).get("center"), arrive_at=spawn_point(e["entrance"])))
        for t in L["transition_actors"]:
            node["room_links"].append(dict(layer=L["label"], actor=t["actor"], pos=t["pos"], rooms=[t["front_room"], t["back_room"]],
                                           decoded=t.get("decoded")))
    for room in sc["rooms"]:
        for label, L in room["layers"].items():
            if L["header_source"] != "own" and label != "child_day":
                continue
            for a in L["actors"]:
                d = a.get("decoded") or {}
                if d.get("kind") == "grotto":
                    node["edges"].append(dict(layer=label, via="grotto_hole", room=room["room"], at=a["pos"], entrance=d.get("entrance"),
                                              entrance_enum=d.get("entrance_enum"), to_scene=d.get("dest_scene"),
                                              to_scene_enum=d.get("dest_scene_enum"), to_spawn=d.get("dest_spawn"),
                                              requires=d.get("requires"), return_data=d.get("return_data"),
                                              arrive_at=spawn_point(d["entrance"]) if d.get("entrance") is not None else None))
    # collapse identical edges repeated across layers
    seen, uniq = {}, []
    for e in node["edges"]:
        k = (e["via"], e.get("exit_index"), e.get("entrance"), tuple(e.get("at") or ()))
        if k in seen:
            seen[k]["layers"].append(e["layer"])
            continue
        e = dict(e)
        e["layers"] = [e.pop("layer")]
        seen[k] = e
        uniq.append(e)
    node["edges"] = uniq
    seen, uniq = {}, []
    for e in node["room_links"]:
        k = (e["actor"], tuple(e["pos"]), tuple(e["rooms"]))
        if k in seen:
            seen[k]["layers"].append(e["layer"])
            continue
        e = dict(e)
        e["layers"] = [e.pop("layer")]
        seen[k] = e
        uniq.append(e)
    node["room_links"] = uniq
    scene_graph.append(node)

# ------------------------------------------------------------------ warps
writes = jload(os.path.join(OUT, "code", "code_entrance_writes.json"))
warp_songs = []
songs = ["Minuet of Forest", "Bolero of Fire", "Serenade of Water", "Requiem of Spirit", "Nocturne of Shadow", "Prelude of Light"]
ebe = D.entrance_by_enum()
for song, en in zip(songs, D.warp_song_entrances()):
    i = ebe[en]
    warp_songs.append(dict(song=song, entrance=i, entrance_enum=en, arrive_at=spawn_point(i),
                           blocked_when="room behavior warp_songs_disabled is true (see scenes/*.json rooms[].layers[].behavior)"))
blue_warps = [w for w in writes if w["owner"] == "Door_Warp1" and w["targets"]]
owls = [w for w in writes if w["targets"] and (w["owner"] == "En_Owl" or (w["conditions_nearby"] and "_OWL" in w["conditions_nearby"][-1]))]
cutscene_dest = [w for w in writes if w["targets"] and w["file"].endswith("z_demo.c")]
grottos = [dict(scene=sid, scene_enum=scenes[sid]["enum"], room=h["room"], pos=h["pos"], **{k: h["decoded"].get(k) for k in
           ("visibility", "requires", "entrance", "entrance_enum", "dest_scene_enum", "dest_spawn", "generic_grotto_chest_if_any")},
           arrive_at=spawn_point(h["decoded"]["entrance"]) if h["decoded"].get("entrance") is not None else None)
           for (sid, rb), h in sorted(grotto_holes.items(), key=lambda kv: kv[0])]
warp_pads = []
for (sid, kind), refs in by_scene_kind.items():
    if kind == "warp":
        for r in dedupe(refs):
            warp_pads.append(dict(scene=sid, scene_enum=scenes[sid]["enum"], room=r["room"], pos=r["pos"], layers=r["layers"],
                                  warp_type=r["decoded"]["warp_type"]))
warps = dict(
    warp_songs=warp_songs,
    blue_warps_and_boss_exits=dict(placed_actors=sorted(warp_pads, key=lambda w: w["scene"]), code_destinations=blue_warps),
    owl_flights=owls,
    cutscene_destinations=cutscene_dest,
    grottos=grottos,
    other_code_entrance_writes="code/code_entrance_writes.json (every assignment of nextEntranceIndex & co. in the decomp, with nearby conditions)",
    void_out="touching a polygon whose surface floor_property is 5 (or 12) respawns Link at the last entrance; falling below y=-4000 also voids",
    savewarp="saving/dying in a dungeon returns to its entrance; see logic/world_graph.json regions[].savewarp",
)

# ------------------------------------------------------------------ write
jdump(items, "items.json")
jdump(dict(regions=graph_regions), "logic", "world_graph.json")
jdump(helpers, "logic", "helpers.json")
jdump(scene_graph, "scene_graph.json")
jdump(warps, "warps.json")
idx2 = []
for row in index:
    row = dict(row)
    row["name"] = scene_names.get(row["scene_id"])
    idx2.append(row)
jdump(idx2, "scenes", "_index.json")

stats = dict(item_locations=len(items),
             with_rom_actor=sum(1 for i in items if i.get("rom_actors")),
             rom_link_expected_but_missing=dict(unmatched),
             xflag_index_offset_votes=dict(xflag_offset_votes),
             regions=len(graph_regions),
             region_exits=sum(len(r["exits"]) for r in graph_regions),
             exits_with_entrance_index=sum(1 for r in graph_regions for e in r["exits"] if "entrance" in e),
             exits_with_loading_zone=sum(1 for r in graph_regions for e in r["exits"] if e.get("loading_zones")),
             scene_edges=sum(len(n["edges"]) for n in scene_graph))
jdump(stats, "build_stats.json")
print(json.dumps(stats, indent=1))
