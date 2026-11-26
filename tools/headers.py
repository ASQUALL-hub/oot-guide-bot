"""Read names/enums out of the zeldaret/oot decomp headers (as plain text, never executed)."""
import os
import re


def _read(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


def strip_debug_blocks(text, keep_debug=False):
    """Drop `#if DEBUG_ASSETS ... #endif` style blocks (retail ROM has none of them)."""
    out, stack = [], []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#if"):
            stack.append("DEBUG" in s and not keep_debug)
            continue
        if s.startswith("#elif") or s.startswith("#else"):
            if stack:
                stack[-1] = not stack[-1] if "DEBUG" in s or s.startswith("#else") else stack[-1]
            continue
        if s.startswith("#endif"):
            if stack:
                stack.pop()
            continue
        if any(stack):
            continue
        out.append(line)
    return "\n".join(out)


def parse_enum(text, enum_name):
    """Return {int value: NAME} for `typedef enum <enum_name> { ... }`."""
    m = re.search(r"typedef enum\s+" + re.escape(enum_name) + r"\s*\{(.*?)\}\s*" + re.escape(enum_name) + r"\s*;", text, re.S)
    if not m:
        m = re.search(r"typedef enum\s*\{(.*?)\}\s*" + re.escape(enum_name) + r"\s*;", text, re.S)
    if not m:
        return {}
    body = m.group(1)
    body = re.sub(r"//[^\n]*", "", body)
    res, cur = {}, -1
    for part in body.split(","):
        part = re.sub(r"/\*.*?\*/", "", part, flags=re.S).strip()
        if not part or part.startswith("#"):
            continue
        part = part.splitlines()[-1].strip() if "\n" in part else part
        mm = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:=\s*(.+))?$", part)
        if not mm:
            continue
        name, val = mm.group(1), mm.group(2)
        if val is not None:
            val = val.strip()
            try:
                cur = int(val, 0)
            except ValueError:
                rev = {v: k for k, v in res.items()}
                if val in rev:
                    cur = rev[val]
                else:
                    cur += 1
        else:
            cur += 1
        res.setdefault(cur, name)
    return res


def table_entries(path, macro_prefix):
    """Parse `/* 0xNN */ DEFINE_X(args...)` lines -> list of (index, macro, [args])."""
    text = strip_debug_blocks(_read(path))
    out = []
    for m in re.finditer(r"/\*\s*(0x[0-9A-Fa-f]+)\s*\*/\s*(" + macro_prefix + r"\w*)\((.*?)\)\s*(?://.*)?$", text, re.M):
        idx = int(m.group(1), 16)
        args = [a.strip() for a in m.group(3).split(",")]
        out.append((idx, m.group(2), args))
    return out


class Decomp:
    def __init__(self, root):
        self.root = root
        inc = os.path.join(root, "include")
        t = os.path.join(inc, "tables")
        self.scenes = {}
        for idx, mac, a in table_entries(os.path.join(t, "scene_table.h"), "DEFINE_SCENE"):
            self.scenes[idx] = dict(file=a[0], title=a[1], enum=a[2], draw_config=a[3])
        self.entrances = {}
        for idx, mac, a in table_entries(os.path.join(t, "entrance_table.h"), "DEFINE_ENTRANCE"):
            if mac == "DEFINE_ENTRANCE":
                self.entrances[idx] = dict(enum=a[0], scene=a[1], spawn=int(a[2], 0), continue_bgm=a[3] == "true",
                                           title_card=a[4] == "true", trans_end=a[5], trans_start=a[6])
        self.actors = {}
        for idx, mac, a in table_entries(os.path.join(t, "actor_table.h"), "DEFINE_ACTOR"):
            if mac == "DEFINE_ACTOR_UNSET":
                self.actors[idx] = dict(name=None, enum=a[0])
            else:
                self.actors[idx] = dict(name=a[0], enum=a[1])
        self.objects = {}
        for idx, mac, a in table_entries(os.path.join(t, "object_table.h"), "DEFINE_OBJECT"):
            self.objects[idx] = dict(name=None if mac.endswith("UNSET") else a[0], enum=a[-1] if mac.endswith("UNSET") else a[1])
        item_h = _read(os.path.join(inc, "item.h"))
        self.item_ids = parse_enum(item_h, "ItemID")
        self.gi_ids = parse_enum(item_h, "GetItemID")
        self.item00 = parse_enum(_read(os.path.join(inc, "z_en_item00.h")), "Item00Type")
        bg = _read(os.path.join(inc, "bgcheck.h"))
        self.floor_types = parse_enum(bg, "FloorType")
        self.wall_types = parse_enum(bg, "WallType")
        self.floor_props = parse_enum(bg, "FloorProperty")
        self.materials = parse_enum(bg, "SurfaceMaterial")
        self.floor_effects = parse_enum(bg, "FloorEffect")
        self._actor_src_cache = {}

    def entrance_by_enum(self):
        return {v["enum"]: k for k, v in self.entrances.items()}

    def actor_dir(self, actor_name):
        return os.path.join(self.root, "src", "overlays", "actors", "ovl_" + actor_name)

    def actor_description(self, actor_name):
        d = self.actor_dir(actor_name)
        if not os.path.isdir(d):
            return None
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".c"):
                txt = _read(os.path.join(d, fn))[:1500]
                m = re.search(r"Description:\s*(.*?)\n\s*\*\s*(?:\n|/)", txt, re.S)
                if m:
                    return re.sub(r"\s*\n\s*\*\s*", " ", m.group(1)).strip()
        return None

    def get_item_table(self):
        """sGetItemTable from z_player.c -> list indexed by (GI - 1)."""
        txt = _read(os.path.join(self.root, "src", "overlays", "actors", "ovl_player_actor", "z_player.c"))
        m = re.search(r"static GetItemEntry sGetItemTable\[\] = \{(.*?)\n\};", txt, re.S)
        out = []
        for mm in re.finditer(r"GET_ITEM\((.*?)\)\s*,|GET_ITEM_NONE", m.group(1)):
            if mm.group(0).startswith("GET_ITEM_NONE"):
                out.append(None)
            else:
                a = [x.strip() for x in mm.group(1).split(",")]
                out.append(dict(item=a[0], object=a[1], draw=a[2], text_id=int(a[3], 0), field=a[4], chest_anim=a[5]))
        return out

    def warp_song_entrances(self):
        txt = _read(os.path.join(self.root, "src", "overlays", "actors", "ovl_player_actor", "z_player.c"))
        m = re.search(r"static s16 sWarpSongEntrances\[\] = \{(.*?)\};", txt, re.S)
        return [x.strip() for x in m.group(1).split(",") if x.strip()]

    def grotto_entrances(self):
        txt = _read(os.path.join(self.root, "src", "overlays", "actors", "ovl_Door_Ana", "z_door_ana.c"))
        m = re.search(r"static s16 sGrottoEntrances\[\] = \{(.*?)\};", txt, re.S)
        return [x.strip() for x in m.group(1).split(",") if x.strip()]
