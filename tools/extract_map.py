"""Extract a bot-readable world map from an OoT NTSC-J 1.0 ROM.

usage: python -I extract_map.py <tools_dir> <decomp_root> <rom> <out_dir>
"""
import sys
import os
import json
import struct

sys.path.insert(0, sys.argv[1])
from ootrom import OotRom, u8, s8, u16, s16, u32  # noqa: E402
from headers import Decomp  # noqa: E402
import decode  # noqa: E402

DECOMP, ROM_PATH, OUT = sys.argv[2], sys.argv[3], sys.argv[4]
VER = "ntsc-1.0"
R = OotRom(ROM_PATH, os.path.join(DECOMP, "baseroms", VER, "segments.csv"), 0x7430)
D = Decomp(DECOMP)
CODE = R.file("code")
GI_TABLE = D.get_item_table()
ENTR_BY_ENUM = D.entrance_by_enum()
SCENE_ENUM_TO_ID = {v["enum"]: k for k, v in D.scenes.items()}

SETUP_LABELS = ["child_day", "child_night", "adult_day", "adult_night"]


def setup_label(i):
    return SETUP_LABELS[i] if i < 4 else f"cutscene_{i - 4}"


def find_all(hay, needle):
    out, i = [], hay.find(needle)
    while i != -1:
        out.append(i)
        i = hay.find(needle, i + 1)
    return out


# ---------------------------------------------------------------- code tables
def find_scene_table():
    e = R.by_name["ydan_scene"]
    off = find_all(CODE, struct.pack(">II", e[1], e[2]))
    assert len(off) == 1, off
    off = off[0]
    rows = []
    while True:
        vs, ve, ts, te = struct.unpack_from(">IIII", CODE, off + len(rows) * 0x14)
        if vs not in R.by_vrom and vs != 0:
            break
        rows.append(dict(scene_vrom=vs, title_vrom=ts, unk10=CODE[off + len(rows) * 0x14 + 0x10],
                         draw_config=CODE[off + len(rows) * 0x14 + 0x11], unk12=CODE[off + len(rows) * 0x14 + 0x12]))
        if len(rows) > 0x80:
            break
    return off, rows


def find_entrance_table():
    want = []
    for i in range(16):
        e = D.entrances[i]
        want.append((SCENE_ENUM_TO_ID[e["scene"]], e["spawn"]))
    for cand in range(0, len(CODE) - 64, 2):
        if all(CODE[cand + 4 * i] == want[i][0] and CODE[cand + 4 * i + 1] == want[i][1] for i in range(16)):
            # make sure the field also looks right for a bit
            rows = []
            for i in range(len(D.entrances)):
                o = cand + 4 * i
                rows.append(dict(scene=s8(CODE, o), spawn=s8(CODE, o + 1), field=u16(CODE, o + 2)))
            return cand, rows
    raise RuntimeError("entrance table not found")


def find_actor_table():
    e = R.by_name["ovl_En_Test"]
    off = find_all(CODE, struct.pack(">II", e[1], e[2]))[0] - 2 * 0x20
    rows = []
    for i in range(len(D.actors)):
        o = off + i * 0x20
        vs, ve, vrs, vre, ram, init, name, alloc = struct.unpack_from(">IIIIIIIH", CODE, o)
        rows.append(dict(vrom=vs, overlay=R.name_at_vrom(vs) if vs else None, vram=vrs, init_info_vram=init, alloc=alloc))
    return off, rows


def find_object_table():
    e = R.by_name["gameplay_keep"]
    off = find_all(CODE, struct.pack(">II", e[1], e[2]))[0] - 8
    rows = []
    for i in range(len(D.objects)):
        vs, ve = struct.unpack_from(">II", CODE, off + i * 8)
        rows.append(R.name_at_vrom(vs) if vs else None)
    return off, rows


# ---------------------------------------------------------------- scene parsing
def seg_off(ptr, seg):
    if ptr == 0:
        return None
    assert (ptr >> 24) == seg, hex(ptr)
    return ptr & 0xFFFFFF


def read_commands(buf, off):
    cmds = []
    while True:
        c, d1, d2 = buf[off], buf[off + 1], u32(buf, off + 4)
        cmds.append((c, d1, d2))
        if c == 0x14 or len(cmds) > 64:
            break
        off += 8
    return cmds


def actor_entry(buf, o):
    aid, x, y, z, rx, ry, rz, p = struct.unpack_from(">hhhhhhhH", buf, o)
    return aid, (x, y, z), (rx, ry, rz), p


def actor_name(aid):
    a = D.actors.get(aid & 0xFFFF)
    return a["name"] if a and a["name"] else (a["enum"] if a else f"UNKNOWN_{aid:#x}")


def binang_deg(a):
    return round((a & 0xFFFF) * 360.0 / 65536.0, 1)


def parse_actor_list(buf, off, n, scene_ctx):
    out = []
    for i in range(n):
        aid, pos, rot, p = actor_entry(buf, off + i * 16)
        name = actor_name(aid)
        ent = dict(index=i, id=aid, actor=name, pos=list(pos), rot=list(rot), rot_y_deg=binang_deg(rot[1]),
                   params=f"{p:#06x}")
        dec = decode.decode_actor(name, p, rot, scene_ctx)
        if dec:
            ent["decoded"] = dec
        out.append(ent)
    return out


def parse_collision(buf, off):
    mn = struct.unpack_from(">hhh", buf, off)
    mx = struct.unpack_from(">hhh", buf, off + 6)
    nv = u16(buf, off + 0xC)
    vtx = seg_off(u32(buf, off + 0x10), 2)
    npoly = u16(buf, off + 0x14)
    polys = seg_off(u32(buf, off + 0x18), 2)
    surf = seg_off(u32(buf, off + 0x1C), 2)
    nwb = u16(buf, off + 0x24)
    wbo = seg_off(u32(buf, off + 0x28), 2)
    verts = [list(struct.unpack_from(">hhh", buf, vtx + 6 * i)) for i in range(nv)]
    plist, max_surf = [], -1
    for i in range(npoly):
        o = polys + 16 * i
        t, a, b, c = struct.unpack_from(">HHHH", buf, o)
        nx, ny, nz, dist = struct.unpack_from(">hhhh", buf, o + 8)
        plist.append(dict(surface=t, v=[a & 0x1FFF, b & 0x1FFF, c & 0x1FFF], flags_a=a >> 13, flags_b=b >> 13,
                          normal=[round(nx / 32767, 4), round(ny / 32767, 4), round(nz / 32767, 4)], dist=dist))
        max_surf = max(max_surf, t)
    surfaces = []
    for i in range(max_surf + 1):
        w0, w1 = struct.unpack_from(">II", buf, surf + 8 * i)
        surfaces.append(decode.surface(w0, w1, D))
    wbs = []
    for i in range(nwb):
        xmin, ysurf, zmin, xl, zl = struct.unpack_from(">hhhhh", buf, wbo + 16 * i)
        props = u32(buf, wbo + 16 * i + 12)
        room = (props >> 13) & 0x3F
        wbs.append(dict(x_min=xmin, y_surface=ysurf, z_min=zmin, x_len=xl, z_len=zl,
                        room=("all" if room == 0x3F else room), bg_cam=props & 0xFF, light=(props >> 8) & 0x1F,
                        disabled=bool(props & (1 << 19))))
    return dict(bounds_min=list(mn), bounds_max=list(mx), vertices=verts, polygons=plist, surfaces=surfaces,
                waterboxes=wbs)


def exit_zones(col):
    zones = {}
    for p in col["polygons"]:
        ex = col["surfaces"][p["surface"]]["exit_index"]
        if ex:
            z = zones.setdefault(ex, dict(polys=0, mn=[1e9] * 3, mx=[-1e9] * 3, sum=[0, 0, 0], n=0))
            z["polys"] += 1
            for vi in p["v"]:
                v = col["vertices"][vi]
                for k in range(3):
                    z["mn"][k] = min(z["mn"][k], v[k])
                    z["mx"][k] = max(z["mx"][k], v[k])
                    z["sum"][k] += v[k]
                z["n"] += 1
    return {ex: dict(polygon_count=z["polys"], bbox_min=z["mn"], bbox_max=z["mx"],
                     center=[round(z["sum"][k] / z["n"]) for k in range(3)]) for ex, z in zones.items()}


def entrance_info(idx, ENTR):
    if idx < 0 or idx >= len(ENTR):
        return dict(entrance=idx, valid=False)
    e = ENTR[idx]
    h = D.entrances.get(idx, {})
    sc = D.scenes.get(e["scene"], {})
    return dict(entrance=idx, entrance_hex=f"{idx:#05x}", entrance_enum=h.get("enum"), dest_scene=e["scene"],
                dest_scene_enum=sc.get("enum"), dest_spawn=e["spawn"])


def parse_scene(sid, row, ENTR, spawn_counts):
    sname = R.name_at_vrom(row["scene_vrom"])
    buf = R.file(sname)
    hdr = D.scenes.get(sid, {})
    ctx = dict(scene_id=sid, scene_enum=hdr.get("enum"), entrances=ENTR, decomp=D, gi=GI_TABLE)
    base_cmds = read_commands(buf, 0)
    alt_ptrs = []
    for c, d1, d2 in base_cmds:
        if c == 0x18:
            o = seg_off(d2, 2)
            # count: read until a value that isn't a scene-segment pointer/null
            i = 0
            while o + 4 * i + 4 <= len(buf):
                v = u32(buf, o + 4 * i)
                if v != 0 and (v >> 24) != 2:
                    break
                if v != 0 and (v & 0xFFFFFF) >= len(buf):
                    break
                alt_ptrs.append(v)
                i += 1
                if i >= 20:
                    break
            # trim trailing nulls that are likely just following data
            while alt_ptrs and alt_ptrs[-1] == 0 and len(alt_ptrs) > 3:
                alt_ptrs.pop()
    headers = [("own", 0)]
    for i, p in enumerate(alt_ptrs):
        layer = i + 1
        if p:
            headers.append(("own", seg_off(p, 2)))
        elif layer == 3 and alt_ptrs[1]:
            headers.append(("fallback_adult_day", seg_off(alt_ptrs[1], 2)))
        elif layer < 4:
            headers.append(("fallback_base", 0))
        else:
            headers.append((None, None))
    # make sure we always describe the 4 main layers
    while len(headers) < 4:
        headers.append(("fallback_base", 0))

    room_files = None
    setups = []
    collision = None
    for layer, (src, hoff) in enumerate(headers):
        if src is None:
            continue
        cmds = read_commands(buf, hoff)
        if src.startswith("fallback"):
            # the game executes the base header for everything except the missing alt header
            pass
        st = dict(layer=layer, label=setup_label(layer), header_source=src)
        player_entries, spawn_ptr, exit_ptr, trans = [], None, None, []
        for c, d1, d2 in cmds:
            if c == 0x00:
                o = seg_off(d2, 2)
                for i in range(d1):
                    aid, pos, rot, p = actor_entry(buf, o + 16 * i)
                    player_entries.append(dict(index=i, pos=list(pos), rot_y_deg=binang_deg(rot[1]), params=f"{p:#06x}",
                                               start_mode=(p >> 8) & 0xF, bg_cam=p & 0xFF))
            elif c == 0x03:
                if collision is None:
                    collision = parse_collision(buf, seg_off(d2, 2))
                st["collision_header"] = f"{d2:#010x}"
            elif c == 0x04:
                o = seg_off(d2, 2)
                rf = [R.name_at_vrom(u32(buf, o + 8 * i)) for i in range(d1)]
                room_files = room_files or rf
            elif c == 0x06:
                spawn_ptr = seg_off(d2, 2)
            elif c == 0x07:
                st["special_files"] = dict(navi_quest_hint_file=d1, keep_object=D.objects.get(d2 & 0xFFFF, {}).get("enum"))
            elif c == 0x0E:
                o = seg_off(d2, 2)
                for i in range(d1):
                    q = o + 16 * i
                    fr, fc, br, bc = s8(buf, q), s8(buf, q + 1), s8(buf, q + 2), s8(buf, q + 3)
                    aid, x, y, z, ry, p = struct.unpack_from(">hhhhhH", buf, q + 4)
                    name = actor_name(aid)
                    t = dict(index=i, id=aid, actor=name, pos=[x, y, z], rot_y_deg=binang_deg(ry), params=f"{p:#06x}",
                             front_room=fr, back_room=br, front_bg_cam=fc, back_bg_cam=bc)
                    dec = decode.decode_actor(name, p, (0, ry, 0), ctx)
                    if dec:
                        t["decoded"] = dec
                    trans.append(t)
            elif c == 0x0D:
                o = seg_off(d2, 2)
                paths = []
                while o + 8 <= len(buf) and len(paths) < 64:
                    cnt, ptr = buf[o], u32(buf, o + 4)
                    if cnt == 0 or (ptr >> 24) != 2 or (ptr & 0xFFFFFF) + 6 * cnt > len(buf):
                        break
                    po = ptr & 0xFFFFFF
                    paths.append([list(struct.unpack_from(">hhh", buf, po + 6 * k)) for k in range(cnt)])
                    o += 8
                st["paths"] = paths
            elif c == 0x13:
                exit_ptr = seg_off(d2, 2)
            elif c == 0x15:
                st["sound"] = dict(spec=d1, nature_ambience=(d2 >> 8) & 0xFF, sequence_id=d2 & 0xFF)
            elif c == 0x17:
                st["has_cutscene"] = True
            elif c == 0x19:
                st["misc"] = dict(scene_cam_type=d1, world_map_location=d2 & 0xFF)
            elif c == 0x11:
                st["skybox"] = dict(id=d2 >> 24, weather=(d2 >> 16) & 0xFF, indoors=(d2 >> 8) & 0xFF)
            elif c == 0x10:
                st["time"] = dict(hour=(d2 >> 24) & 0xFF, minute=(d2 >> 16) & 0xFF, speed=(d2 >> 8) & 0xFF)
        st["player_entries"] = player_entries
        nsp = spawn_counts.get(sid, 0)
        st["spawns"] = []
        if spawn_ptr is not None:
            for i in range(nsp):
                if spawn_ptr + 2 * i + 2 > len(buf):
                    break
                st["spawns"].append(dict(spawn=i, player_entry=buf[spawn_ptr + 2 * i], room=buf[spawn_ptr + 2 * i + 1]))
        st["_exit_ptr"] = exit_ptr
        st["transition_actors"] = trans
        setups.append(st)

    zones = exit_zones(collision) if collision else {}
    max_exit = max(zones) if zones else 0
    for st in setups:
        ep = st.pop("_exit_ptr")
        exits = []
        if ep is not None:
            n = max(max_exit, 0)
            # read a few extra entries that actors/cutscenes may use (stop at obviously bogus values)
            extra = 0
            while ep + 2 * (n + extra) + 2 <= len(buf) and extra < 8:
                v = s16(buf, ep + 2 * (n + extra))
                if v <= 0 or v >= len(ENTR):
                    break
                extra += 1
            for i in range(n + extra):
                v = s16(buf, ep + 2 * i)
                e = entrance_info(v, ENTR)
                e["exit_index"] = i + 1
                if (i + 1) in zones:
                    e["loading_zone"] = zones[i + 1]
                else:
                    e["loading_zone"] = None
                    e["note"] = "no collision loading zone; used by an actor/cutscene via the exit list, or unused"
                # the real entrance used depends on the layer: entrance + layer (adult night etc.)
                exits.append(e)
        st["exits"] = exits

    # rooms
    rooms = []
    for ri, rname in enumerate(room_files or []):
        rb = R.file(rname)
        rcmds = read_commands(rb, 0)
        ralt = []
        for c, d1, d2 in rcmds:
            if c == 0x18:
                o = seg_off(d2, 3)
                i = 0
                while o + 4 * i + 4 <= len(rb) and i < 20:
                    v = u32(rb, o + 4 * i)
                    if v != 0 and ((v >> 24) != 3 or (v & 0xFFFFFF) >= len(rb)):
                        break
                    ralt.append(v)
                    i += 1
        room = dict(room=ri, file=rname, layers={})
        for st in setups:
            layer = st["layer"]
            if layer == 0:
                hoff, src = 0, "own"
            else:
                p = ralt[layer - 1] if layer - 1 < len(ralt) else 0
                if p:
                    hoff, src = seg_off(p, 3), "own"
                elif layer == 3 and len(ralt) > 1 and ralt[1]:
                    hoff, src = seg_off(ralt[1], 3), "fallback_adult_day"
                else:
                    hoff, src = 0, "fallback_base"
            cmds = read_commands(rb, hoff)
            L = dict(header_source=src)
            for c, d1, d2 in cmds:
                if c == 0x01:
                    L["actors"] = parse_actor_list(rb, seg_off(d2, 3), d1, ctx)
                elif c == 0x0B:
                    o = seg_off(d2, 3)
                    L["objects"] = [D.objects.get(u16(rb, o + 2 * i), {}).get("enum") for i in range(d1)]
                elif c == 0x08:
                    L["behavior"] = dict(type1=d1, type2=d2 & 0xFF, show_invisible_actors=bool((d2 >> 8) & 1),
                                         warp_songs_disabled=bool((d2 >> 10) & 1))
                elif c == 0x16:
                    L["echo"] = d2 & 0xFF
                elif c == 0x12:
                    L["skybox_disabled"] = bool(d2 >> 24)
                    L["sun_moon_disabled"] = bool((d2 >> 16) & 0xFF)
                elif c == 0x10:
                    L["time"] = dict(hour=(d2 >> 24) & 0xFF, minute=(d2 >> 16) & 0xFF, speed=(d2 >> 8) & 0xFF)
                elif c == 0x05:
                    L["wind"] = list(struct.unpack(">bbbB", struct.pack(">I", d2)))
            L.setdefault("actors", [])
            room["layers"][st["label"]] = L
        rooms.append(room)

    return dict(scene_id=sid, scene_id_hex=f"{sid:#04x}", enum=hdr.get("enum"), file=sname,
                title_card=R.name_at_vrom(row["title_vrom"]) if row["title_vrom"] else None,
                draw_config=hdr.get("draw_config"), room_count=len(rooms),
                layers=setups, rooms=rooms), collision


def main():
    os.makedirs(os.path.join(OUT, "scenes"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "collision"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "tables"), exist_ok=True)
    st_off, scene_rows = find_scene_table()
    en_off, ENTR = find_entrance_table()
    ac_off, actor_rows = find_actor_table()
    ob_off, obj_rows = find_object_table()
    print("scene table @code+%#x (%d)  entrance table @code+%#x  actor table @code+%#x  object table @code+%#x" %
          (st_off, len(scene_rows), en_off, ac_off, ob_off))
    # sanity: compare ROM entrance table with decomp header
    mism = [i for i, e in enumerate(ENTR) if D.entrances.get(i) and
            (SCENE_ENUM_TO_ID.get(D.entrances[i]["scene"]) != e["scene"] or D.entrances[i]["spawn"] != e["spawn"])]
    print("entrance mismatches vs decomp header:", len(mism))

    spawn_counts = {}
    for e in ENTR:
        spawn_counts[e["scene"]] = max(spawn_counts.get(e["scene"], 0), e["spawn"] + 1)

    code_vram = R.vram["code"]
    tables = dict(rom=dict(version=VER, region="JP", sha1=None),
                  code_tables=dict(scene_table_vram=f"{code_vram + st_off:#010x}", entrance_table_vram=f"{code_vram + en_off:#010x}",
                                   actor_overlay_table_vram=f"{code_vram + ac_off:#010x}", object_table_vram=f"{code_vram + ob_off:#010x}"))
    with open(os.path.join(OUT, "tables", "code_tables.json"), "w") as f:
        json.dump(tables, f, indent=1)

    # actors table
    actors = []
    for i, a in D.actors.items():
        row = actor_rows[i] if i < len(actor_rows) else {}
        actors.append(dict(id=i, id_hex=f"{i:#06x}", name=a["name"], enum=a["enum"], overlay=row.get("overlay"),
                           overlay_vram=f"{row['vram']:#010x}" if row.get("vram") else None,
                           description=D.actor_description(a["name"]) if a["name"] else None,
                           param_layout=decode.PARAM_DOCS.get(a["name"])))
    with open(os.path.join(OUT, "tables", "actors.json"), "w") as f:
        json.dump(actors, f, indent=1)
    with open(os.path.join(OUT, "tables", "objects.json"), "w") as f:
        json.dump([dict(id=i, enum=o["enum"], file=obj_rows[i] if i < len(obj_rows) else None) for i, o in D.objects.items()], f, indent=1)
    gi = []
    for i, g in enumerate(GI_TABLE):
        gi.append(dict(get_item_id=i + 1, get_item_hex=f"{i + 1:#04x}", enum=D.gi_ids.get(i + 1), **(g or {})))
    with open(os.path.join(OUT, "tables", "get_items.json"), "w") as f:
        json.dump(gi, f, indent=1)
    with open(os.path.join(OUT, "tables", "items.json"), "w") as f:
        json.dump([dict(item_id=k, enum=v) for k, v in sorted(D.item_ids.items())], f, indent=1)
    with open(os.path.join(OUT, "tables", "collectible_drops.json"), "w") as f:
        json.dump([dict(type=k, enum=v) for k, v in sorted(D.item00.items())], f, indent=1)

    # entrances
    import re

    def base_of(i):
        en = D.entrances.get(i, {}).get("enum")
        if not en:
            return None
        m = re.match(r"(ENTR_.*_\d+)_(\d+)$", en)
        return ENTR_BY_ENUM.get(m.group(1)) if m else i

    entr_out = []
    for i, e in enumerate(ENTR):
        h = D.entrances.get(i, {})
        sc = D.scenes.get(e["scene"], {})
        entr_out.append(dict(entrance=i, entrance_hex=f"{i:#05x}", enum=h.get("enum"), scene=e["scene"],
                             scene_enum=sc.get("enum"), spawn=e["spawn"], field=f"{e['field']:#06x}",
                             continue_bgm=h.get("continue_bgm"), title_card=h.get("title_card"),
                             transition_in=h.get("trans_start"), transition_out=h.get("trans_end"),
                             retail_valid=sc != {} and R.name_at_vrom(scene_rows[e["scene"]]["scene_vrom"]) is not None
                             if 0 <= e["scene"] < len(scene_rows) else False,
                             layer=(i - base_of(i)) if base_of(i) is not None else None,
                             base_entrance=base_of(i)))
    # entrance groups: index N, N+1, N+2, N+3 are the child day/child night/adult day/adult night versions
    with open(os.path.join(OUT, "entrances.json"), "w") as f:
        json.dump(entr_out, f, indent=1)

    index = []
    for sid, row in enumerate(scene_rows):
        if row["scene_vrom"] == 0:
            continue
        sc, col = parse_scene(sid, row, ENTR, spawn_counts)
        tag = f"{sid:02x}_{sc['enum']}"
        with open(os.path.join(OUT, "scenes", tag + ".json"), "w") as f:
            json.dump(sc, f, indent=1)
        if col:
            with open(os.path.join(OUT, "collision", tag + ".json"), "w") as f:
                json.dump(col, f, separators=(",", ":"))
        nact = sum(len(L["actors"]) for r in sc["rooms"] for L in r["layers"].values())
        index.append(dict(scene_id=sid, enum=sc["enum"], file=sc["file"], rooms=sc["room_count"],
                          layers=[L["label"] for L in sc["layers"]], scene_json=f"scenes/{tag}.json",
                          collision_json=f"collision/{tag}.json" if col else None))
        print(f"{tag}: rooms={sc['room_count']} layers={len(sc['layers'])} actors={nact} exits={len(sc['layers'][0]['exits'])}")
    with open(os.path.join(OUT, "scenes", "_index.json"), "w") as f:
        json.dump(index, f, indent=1)


if __name__ == "__main__":
    main()
