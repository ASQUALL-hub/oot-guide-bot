"""Decode actor params and collision surface types into readable dicts.

Every bit layout here was taken from the zeldaret/oot decomp source of the
actor in question (src/overlays/actors/ovl_<Actor>/).
"""
# Actor-local enums this module reads. make_metadata.py exports exactly these into the metadata pack,
# so a ROM-only build can decode params without the decomp source. Add new ones here.
ACTOR_ENUMS = [
    ("Item_Etcetera", "ItemEtceteraType"), ("En_Kusa", "EnKusaType"), ("En_Wonder_Item", "EnWonderItemMode"),
    ("En_Wonder_Item", "EnWonderItemDrop"), ("En_G_Switch", "EnGSwitchType"), ("En_Door", "EnDoorType"),
    ("Door_Shutter", "DoorShutterType"), ("En_Holl", "EnHollType"), ("Door_Warp1", "DoorWarp1Type"),
    ("En_Dns", "EnDnsType"), ("En_GirlA", "EnGirlAShopItem"), ("Obj_Switch", "ObjSwitchType"),
    ("Obj_Switch", "ObjSwitchSubType"), ("Bg_Breakwall", "BombableWallType"),
]
ACTOR_PREFIXED = [("En_Owl", "OWL_", "OWL_REPEAT")]


def _enum(decomp, actor, enum_name):
    return decomp.actor_enum(actor, enum_name)


def _prefixed_list(decomp, actor, prefix, stop):
    return decomp.actor_prefixed(actor, prefix, stop)


def bits(v, shift, n):
    return (v >> shift) & ((1 << n) - 1)


def gi_info(gi, ctx):
    D = ctx["decomp"]
    g = ctx["gi"][gi - 1] if 0 < gi <= len(ctx["gi"]) else None
    out = dict(get_item_id=gi, get_item=D.gi_ids.get(gi))
    if g:
        out["item"] = g["item"]
    return out


def entrance_ref(idx, ctx):
    E = ctx["entrances"]
    D = ctx["decomp"]
    if not (0 <= idx < len(E)):
        return dict(entrance=idx)
    e = E[idx]
    return dict(entrance=idx, entrance_enum=D.entrances.get(idx, {}).get("enum"), dest_scene=e["scene"],
                dest_scene_enum=D.scenes.get(e["scene"], {}).get("enum"), dest_spawn=e["spawn"])


ITEM00_COLLECTIBLE_FLAG_TYPES = None


def item00(dtype, flag, ctx, prefix="drop"):
    D = ctx["decomp"]
    return {f"{prefix}_type": dtype, f"{prefix}": D.item00.get(dtype, "random/none" if dtype >= 0x1A else None),
            "collectible_flag": flag}


PARAM_DOCS = {
    "En_Box": "chest. type=bits12-15, get_item_id=bits5-11, treasure_flag=bits0-4 (scene-local 'chest opened' flag)",
    "En_Item00": "freestanding collectible. drop type=bits0-7 (Item00Type), collectible_flag=bits8-13 (scene-local; persistent for heart pieces/keys)",
    "En_Sw": "skullwalltula / gold skulltula. type=bits13-15 (0 enemy, 1 gold on wall, 2 gold hidden until revealed, 3-4 gold that jumps out on reveal), gs_flag_index=bits8-12 minus 1, gs_bit_mask=bits0-7",
    "En_Si": "gold skulltula token. gs_flag_index=bits8-12, gs_bit_mask=bits0-7",
    "Item_Etcetera": "special item on the ground. type=bits0-7 (ItemEtceteraType), treasure_flag=bits8-12",
    "Item_B_Heart": "boss heart container. uses collectible flag 0x1F",
    "Obj_Tsubo": "pot. drop=bits0-4 (Item00Type), object variant=bit8, collectible_flag=bits9-14",
    "Obj_Kibako": "small wooden crate. drop=bits0-4, collectible_flag=bits8-13",
    "Obj_Comb": "beehive. drop=bits0-4, collectible_flag=bits8-13",
    "En_Kusa": "grass/bush. type=bits0-1, drop_table=bits8-11, bit4=random drop",
    "En_Wonder_Item": "invisible item trigger. mode=bits11-15, drop=bits6-10, switch_flag=bits0-5",
    "En_G_Switch": "silver rupee / its counter. type=bits12-15, silver_count=bits6-11, switch_flag=bits0-5",
    "Door_Ana": "grotto hole. fixed destination=bits12-14 (index-1 into sGrottoEntrances, 0 means use rot.z+1), bit9=hidden (bomb/hammer), bit8 only=hidden (Song of Storms), bits0-7 forwarded to the grotto (chest contents/flag)",
    "En_Door": "wooden door. type=bits7-9 (EnDoorType), double=bit6, data=bits0-5 (switch flag if locked, text id-0x200 if checkable)",
    "Door_Shutter": "sliding/dungeon door. type=bits6-9 (DoorShutterType), switch_flag=bits0-5",
    "En_Holl": "room transition plane. type=bits6-8 (EnHollType), switch_flag=bits0-5",
    "Door_Warp1": "warp pad / blue warp. params=DoorWarp1Type",
    "En_Owl": "owl. type=bits6-11, switch_flag=bits0-5",
    "En_Dns": "business scrub (Deku). params=EnDnsType (what it sells)",
    "En_GirlA": "shop item on a shelf. params=EnGirlAShopItem",
    "En_Ishi": "rock. type=bit0 (0 small, 1 large/silver), drop_table=bits8-11 (small rocks), switch flag bits10-15 (large)",
    "Obj_Switch": "switch. type=bits0-2, subtype=bits4-6, frozen=bit7, switch_flag=bits8-13",
    "Bg_Breakwall": "bombable wall. type=bits13-14, switch_flag=bits0-5",
    "Obj_Bombiwa": "bombable boulder. switch_flag=bits0-5",
    "En_Torch": "grotto chest spawner; contents come from the Door_Ana params you entered through",
}


def decode_actor(name, p, rot, ctx):
    D = ctx["decomp"]
    if name == "En_Box":
        typ = bits(p, 12, 4)
        out = dict(kind="chest", chest_type=typ, treasure_flag=bits(p, 0, 5))
        out.update(gi_info(bits(p, 5, 7), ctx))
        return out
    if name == "En_Item00":
        out = dict(kind="collectible")
        out.update(item00(bits(p, 0, 8), bits(p, 8, 6), ctx))
        return out
    if name == "En_Sw":
        q = p
        if q & 0x8000:
            q = (q & 0x1FFF) | ((((q - 0x8000) >> 13) & 7) + 1) << 13
        typ = bits(q, 13, 3)
        if typ == 0:
            return dict(kind="enemy", enemy="Skullwalltula")
        return dict(kind="gold_skulltula", gs_type=typ, gs_flag_index=bits(q, 8, 5) - 1, gs_bit_mask=f"{bits(q, 0, 8):#04x}",
                    note={1: "visible on wall", 2: "hidden until revealed", 3: "jumps out when revealed", 4: "jumps out when revealed"}.get(typ))
    if name == "En_Si":
        return dict(kind="gold_skulltula_token", gs_flag_index=bits(p, 8, 5), gs_bit_mask=f"{bits(p, 0, 8):#04x}")
    if name == "Item_Etcetera":
        t = bits(p, 0, 8)
        return dict(kind="special_item", type=t, type_enum=_enum(D, name, "ItemEtceteraType").get(t), treasure_flag=bits(p, 8, 5))
    if name == "Item_B_Heart":
        return dict(kind="heart_container", collectible_flag=0x1F)
    if name == "Obj_Tsubo":
        out = dict(kind="pot", object_variant=bits(p, 8, 1))
        out.update(item00(bits(p, 0, 5), bits(p, 9, 6), ctx))
        return out
    if name in ("Obj_Kibako", "Obj_Comb"):
        out = dict(kind={"Obj_Kibako": "small_crate", "Obj_Comb": "beehive"}[name])
        out.update(item00(bits(p, 0, 5), bits(p, 8, 6), ctx))
        return out
    if name == "Obj_Kibako2":
        out = dict(kind="large_crate")
        if not (p & 0x8000):
            out["contains"] = decode_actor("En_Sw", p | 0x8000, rot, ctx)
            out["contains"]["spawned_by"] = "breaking this large crate"
        return out
    if name == "Obj_Makekinsuta":
        gs = decode_actor("En_Sw", p | 0x8000, rot, ctx)
        gs["spawned_by"] = "release bugs into this soft soil patch"
        return dict(kind="soft_soil_gs_spawner", contains=gs)
    if name == "En_Wood02":
        out = dict(kind="tree_or_bush", wood_type=bits(p, 0, 8))
        if rot[2] != 0:
            gsp = 0xE000 | ((((rot[2] & 0xFF) << 8) | bits(p, 8, 8)) & 0x1FFF)
            out["contains"] = decode_actor("En_Sw", gsp, rot, ctx)
            out["contains"]["spawned_by"] = "roll into / hit this tree"
        return out
    if name == "En_Shopnuts":
        return dict(kind="business_scrub", sells=_enum(D, "En_Dns", "EnDnsType").get(p, p),
                    note="hides in the ground; deflect its nut or hit it, then it turns into an En_Dns salesman")
    if name == "En_Kusa":
        return dict(kind="grass", type=bits(p, 0, 2), type_enum=_enum(D, name, "EnKusaType").get(bits(p, 0, 2)),
                    drop_table=bits(p, 8, 4), random_drop=bool(bits(p, 4, 1)))
    if name == "En_Wonder_Item":
        return dict(kind="hidden_item_trigger", mode=_enum(D, name, "EnWonderItemMode").get(bits(p, 11, 5), bits(p, 11, 5)),
                    drop=_enum(D, name, "EnWonderItemDrop").get(bits(p, 6, 5), bits(p, 6, 5)), switch_flag=bits(p, 0, 6))
    if name == "En_G_Switch":
        return dict(kind="silver_rupee_system", type=_enum(D, name, "EnGSwitchType").get(bits(p, 12, 4), bits(p, 12, 4)),
                    silver_count=bits(p, 6, 6), switch_flag=bits(p, 0, 6))
    if name == "Door_Ana":
        fixed = bits(p, 12, 3)
        grottos = D.grotto_entrances()
        idx = fixed - 1 if fixed else rot[2] + 1
        dest = grottos[idx] if 0 <= idx < len(grottos) else None
        en = D.entrance_by_enum().get(dest)
        vis = bits(p, 8, 2)
        out = dict(kind="grotto",
                   visibility="open" if vis == 0 else ("hidden: bomb or hammer it open" if vis & 2 else "hidden: play Song of Storms within 200 units"),
                   requires=None if vis == 0 else ("explosive or Megaton Hammer" if vis & 2 else "Song of Storms"),
                   destination_source="params bits12-14" if fixed else "rot.z + 1",
                   destination_entrance_enum=dest)
        if en is not None:
            out.update(entrance_ref(en, ctx))
        chest_table = ["GI_RUPEE_BLUE", "GI_RUPEE_RED", "GI_RUPEE_GOLD", "GI_BOMBS_20", "GI_BOMBS_1", "GI_BOMBS_1", "GI_BOMBS_1", "GI_BOMBS_1"]
        out["generic_grotto_chest_if_any"] = dict(get_item=chest_table[bits(p, 5, 3)], treasure_flag_in_grotto_scene=bits(p, 0, 5))
        out["return_data"] = f"{p:#06x}"
        return out
    if name == "En_Door":
        t = bits(p, 7, 3)
        te = _enum(D, name, "EnDoorType").get(t)
        out = dict(kind="door", door_type=te or t, double_door=bool(bits(p, 6, 1)))
        if te and "LOCKED" in te:
            out["switch_flag"] = bits(p, 0, 6)
            out["requires"] = "small key (unlocks switch flag)"
        elif te and ("CHECKABLE" in te or "EVENING" in te):
            out["text_id"] = f"{bits(p, 0, 6) + 0x200:#06x}"
        return out
    if name == "Door_Shutter":
        t = bits(p, 6, 4)
        te = _enum(D, name, "DoorShutterType").get(t)
        out = dict(kind="dungeon_door", door_type=te or t, switch_flag=bits(p, 0, 6))
        if te == "SHUTTER_KEY_LOCKED":
            out["requires"] = "small key"
        elif te == "SHUTTER_BOSS":
            out["requires"] = "boss key"
        elif te and "CLEAR" in te:
            out["requires"] = "defeat all enemies in the room (clear flag)"
        elif te and "SWITCH" in te:
            out["requires"] = "switch flag set"
        return out
    if name == "En_Holl":
        t = bits(p, 6, 3)
        return dict(kind="room_transition_plane", holl_type=_enum(D, name, "EnHollType").get(t, t), switch_flag=bits(p, 0, 6))
    if name == "Door_Warp1":
        t = p if p < 0x8000 else p - 0x10000
        return dict(kind="warp", warp_type=_enum(D, name, "DoorWarp1Type").get(t, t),
                    note="destination is hard-coded per scene in Door_Warp1; see warps.json")
    if name == "En_Owl":
        t = bits(p, 6, 6)
        return dict(kind="owl", owl_type=_prefixed_list(D, name, "OWL_", "OWL_REPEAT").get(t, t), switch_flag=bits(p, 0, 6))
    if name == "En_Dns":
        return dict(kind="business_scrub", sells=_enum(D, name, "EnDnsType").get(p, p))
    if name == "En_GirlA":
        return dict(kind="shop_item", shop_item=_enum(D, name, "EnGirlAShopItem").get(p, p))
    if name == "En_Ishi":
        t = bits(p, 0, 1)
        out = dict(kind="rock", size="large (needs silver gauntlets)" if t else "small (liftable)")
        if t:
            out["switch_flag"] = bits(p, 10, 6)
        else:
            out["drop_table"] = bits(p, 8, 4)
        return out
    if name == "Obj_Switch":
        t = bits(p, 0, 3)
        return dict(kind="switch", switch_type=_enum(D, name, "ObjSwitchType").get(t, t),
                    subtype=_enum(D, name, "ObjSwitchSubType").get(bits(p, 4, 3), bits(p, 4, 3)),
                    frozen=bool(bits(p, 7, 1)), switch_flag=bits(p, 8, 6))
    if name == "Bg_Breakwall":
        # its collider accepts DMG_EXPLOSIVE | DMG_HAMMER_SWING (0x48) and any hit breaks it (BgBreakwall_Wait)
        return dict(kind="bombable_wall", wall_type=_enum(D, name, "BombableWallType").get(bits(p, 13, 2), bits(p, 13, 2)),
                    switch_flag=bits(p, 0, 6), requires="explosive or Megaton Hammer swing")
    if name == "En_Okarina_Tag":
        # z_en_okarina_tag.c: type = params bits 10-15, song = bits 6-9, switch flag = bits 0-5 (0x3F = none)
        t, song, flag = bits(p, 10, 6), bits(p, 6, 4), bits(p, 0, 6)
        songs = ["Saria's Song", "Epona's Song", "Zelda's Lullaby", "Sun's Song", "Song of Time", "Song of Storms",
                 "Scarecrow's Song"]
        fixed = {1: ("Zelda's Lullaby", "sets its switch flag"),
                 2: ("Song of Storms", "child only: speeds up the Kakariko windmill and drains the well"),
                 4: ("Song of Time", "opens the Door of Time (with the three Spiritual Stones)"),
                 6: ("Zelda's Lullaby", "opens the Royal Family's Tomb"),
                 7: ("any song" if song == 0xF else (songs[song] if song < len(songs) else song), "sets its switch flag"),
                 5: (None, "shows a hint message (text 0x5021)")}
        play, effect = fixed.get(t, (None, "unused type (the actor deletes itself)"))
        rng = 90 + max(rot[2], 0) * 40
        return dict(kind="ocarina_spot", spot_type=t, play=play, effect=effect,
                    switch_flag=None if flag == 0x3F else flag,
                    range=f"within {rng} units horizontally and 80 vertically")
    if name == "Obj_Timeblock":
        return dict(kind="song_of_time_block", switch_flag=bits(p, 0, 6), size="large" if bits(p, 8, 1) == 0 else "small",
                    note="play the Song of Time near it to make it appear or disappear. Whether it starts visible depends "
                         "on its switch flag, params bit 15 and (for some) Link's age: ObjTimeblock_CalculateIsVisible")
    if name == "Obj_Bombiwa":
        return dict(kind="bombable_boulder", switch_flag=bits(p, 0, 6), requires="explosive or hammer")
    if name == "En_Torch":
        return dict(kind="grotto_chest_spawner")
    if name == "En_Cow":
        return dict(kind="cow", note="play Epona's Song for milk")
    if name == "Bg_Toki_Swd":
        return dict(kind="master_sword_pedestal")
    return None


SURFACE_NOTES = {
    "floor_property": {5: "void out (respawn at last entrance)", 12: "falling into this triggers the polygon's exit"},
    # From the decomp: z_bgcheck.c D_80119D90 maps wall type -> WALL_FLAG_*, and z_player.c acts on the flags.
    # FLAG_0 (types 1-3) disables ledge grabs on that wall; FLAG_1 (type 2) and FLAG_3 (type 4) start a
    # face-the-wall climb; FLAG_2 alone (type 3) grabs from the top to climb down backwards.
    "wall_type": {1: "no ledge grab / climb-up on this wall",
                  2: "ladder: climbable (no ledge grab)",
                  3: "ladder top: grab from above to climb down (no ledge grab)",
                  4: "climbable surface (vines / climb wall)",
                  5: "crawlspace (child only)", 6: "crawlspace (child only)"},
}


def surface(w0, w1, D):
    fp = bits(w0, 26, 4)
    wt = bits(w0, 21, 5)
    return dict(
        raw=[f"{w0:#010x}", f"{w1:#010x}"],
        bg_cam=bits(w0, 0, 8), exit_index=bits(w0, 8, 5), floor_type=bits(w0, 13, 5),
        wall_type=wt, wall_note=SURFACE_NOTES["wall_type"].get(wt),
        floor_property=fp, floor_note=SURFACE_NOTES["floor_property"].get(fp),
        is_soft=bool(bits(w0, 30, 1)), horse_blocked=bool(bits(w0, 31, 1)),
        material=D.materials.get(bits(w1, 0, 4), bits(w1, 0, 4)), floor_effect=bits(w1, 4, 2),
        light_setting=bits(w1, 6, 5), echo=bits(w1, 11, 6), hookshotable=bool(bits(w1, 17, 1)),
        conveyor_speed=bits(w1, 18, 3), conveyor_direction_binang=bits(w1, 21, 6) * (0x10000 // 64),
    )
