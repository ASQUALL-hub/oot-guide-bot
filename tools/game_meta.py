"""MAINTAINERS ONLY (called by make_metadata.py): the game's own item and combat rules, read from the decomp
source as data (regex over C tables, never compiled or run). Output goes to data/meta/game_rules.json, so a
ROM-only build has it. Every table records the file it came from."""
import ast
import os
import re

INV = os.path.join("src", "code", "z_inventory.c")
KALEIDO = os.path.join("src", "overlays", "misc", "ovl_kaleido_scope", "z_kaleido_scope.c")
PLAYER = os.path.join("src", "overlays", "actors", "ovl_player_actor", "z_player.c")
BTLTBLS = os.path.join("src", "code", "z_collision_btltbls.c")
COLCHK_H = os.path.join("include", "collision_check.h")
SONGS = os.path.join("src", "audio", "game", "general.c")
ITEM_H = os.path.join("include", "item.h")
HOOK = os.path.join("src", "overlays", "actors", "ovl_Arms_Hook", "z_arms_hook.c")


def _read(root, rel):
    with open(os.path.join(root, rel), encoding="utf-8") as f:
        return f.read()


def _block(src, var):
    m = re.search(r"\b%s\s*(?:\[[^\]]*\])+\s*=\s*\{(.*?)\n\};" % re.escape(var), src, re.S)
    assert m, var
    return m.group(1)


def commented_table(src, var):
    """Rows written as `VALUE, // KEY` -> [(key, value)]."""
    return [(k.strip(), v) for v, k in re.findall(r"^\s*([A-Za-z_0-9]+),\s*//\s*(.+?)\s*$", _block(src, var), re.M)]


def enum_list(src, name_prefix):
    return re.findall(r"/\*\s*0x([0-9A-Fa-f]+)\s*\*/\s*(%s\w+)" % name_prefix, src)


def dmg_constants(root):
    h = _read(root, COLCHK_H)
    defs = dict(re.findall(r"#define (DMG_\w+)\s+(.+?)\s*$", h, re.M))
    vals = {}

    def ev(expr):
        tree = ast.parse(expr.strip(), mode="eval")

        def go(n):
            if isinstance(n, ast.Expression):
                return go(n.body)
            if isinstance(n, ast.Constant):
                return n.value
            if isinstance(n, ast.Name):
                if n.id not in vals:
                    vals[n.id] = ev(defs[n.id])
                return vals[n.id]
            if isinstance(n, ast.BinOp):
                a, b = go(n.left), go(n.right)
                return {ast.BitOr: a | b, ast.BitAnd: a & b, ast.LShift: a << b}[type(n.op)]
            if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Invert):
                return ~go(n.operand) & 0xFFFFFFFF
            raise ValueError(ast.dump(n))
        return go(tree) & 0xFFFFFFFF
    for k in defs:
        if k != "DMG_ENTRY" and "(" not in k:
            vals[k] = ev(defs[k])
    bits = {k: v for k, v in vals.items() if v and (v & (v - 1)) == 0}
    order = [k for k, _ in sorted(bits.items(), key=lambda kv: kv[1])]
    return vals, order, ev


def decode_flags(mask, order, vals):
    if mask == 0:
        return []
    for combo in ("DMG_DEFAULT",):
        if mask == vals.get(combo):
            return ["everything except shield and mirror ray (DMG_DEFAULT)"]
    return [k for k in order if mask & vals[k]]


def damage_row_names(root):
    src = _read(root, BTLTBLS)
    first = re.search(r"\{\s*\{(.*?)\}\s*\}", src, re.S).group(1)
    return [c.strip() for c in re.findall(r"/\*\s*(.+?)\s*\*/\s*DMG_ENTRY", first)]


def parse_damage_block(text):
    return [(c.strip(), d, r) for c, d, r in re.findall(r"/\*\s*(.+?)\s*\*/\s*DMG_ENTRY\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", text)]


def _num(tok, consts):
    tok = tok.strip()
    try:
        return int(tok, 0)
    except ValueError:
        return consts.get(tok, tok)


def actor_enum_values(src):
    """Enum members in an actor file, so DMG_ENTRY(2, ENWF_DMG_REACT_FIRE) can be shown as a number too."""
    out = {}
    for body in re.findall(r"typedef enum[^{]*\{(.*?)\}", src, re.S):
        i = 0
        for name, val in re.findall(r"^\s*(?:/\*[^*]*\*/\s*)?([A-Z][A-Z0-9_]+)\s*(?:=\s*([^,\n]+))?,?", body, re.M):
            if val:
                try:
                    i = int(val.strip(), 0)
                except ValueError:
                    continue
            out[name] = i
            i += 1
    for name, val in re.findall(r"#define\s+([A-Z][A-Z0-9_]+)\s+(0x[0-9A-Fa-f]+|\d+)\b", src):
        out[name] = int(val, 0)
    return out


ELEM_RE = re.compile(r"ELEM_MATERIAL_\w+,\s*\{\s*([^,{}]+),\s*([^,{}]+),\s*([^{}]+?)\s*\},\s*"
                     r"\{\s*([^,{}]+),\s*([^,{}]+),\s*([^{}]+?)\s*\},\s*([\w| ]+?),\s*([\w| ]+?),")


def actor_rules(root, dmg_vals, dmg_order, ev, row_names):
    base = os.path.join(root, "src", "overlays", "actors")
    presets_src = _read(root, BTLTBLS)
    presets = [parse_damage_block(b) for b in re.findall(r"\{\s*\{(.*?)\}\s*\}", presets_src, re.S)]
    out = {}
    for d in sorted(os.listdir(base)):
        if not d.startswith("ovl_"):
            continue
        actor = d[4:]
        texts = []
        for fn in sorted(os.listdir(os.path.join(base, d))):
            if fn.endswith((".c", ".h")):
                with open(os.path.join(base, d, fn), encoding="utf-8") as f:
                    texts.append((fn, f.read()))
        src = "\n".join(t for _, t in texts)
        consts = actor_enum_values(src)
        rec = {}
        tables = []
        for m in re.finditer(r"static DamageTable (\w+)(\[\])?\s*=\s*\{(.*?)\n\};", src, re.S):
            blocks = re.findall(r"\{(.*?)\}", m.group(3), re.S) if m.group(2) else [m.group(3)]
            for i, b in enumerate(blocks):
                rows = parse_damage_block(b)
                if len(rows) == 32:
                    tables.append(dict(name=m.group(1) + (f"[{i}]" if m.group(2) else ""), rows=rows))
        for m in re.finditer(r"DamageTable_Get\(\s*(0x[0-9A-Fa-f]+|\d+)\s*\)", src):
            n = int(m.group(1), 0)
            if n < len(presets):
                tables.append(dict(name=f"preset {n} (z_collision_btltbls.c)", rows=presets[n]))
        if tables:
            seen, rec["damage_tables"] = set(), []
            for t in tables:
                key = t["name"]
                if key in seen:
                    continue
                seen.add(key)
                hurt, react = {}, {}
                for (cmt, dmg, rea), label in zip(t["rows"], row_names):
                    dv, rv = _num(dmg, consts), _num(rea, consts)
                    if isinstance(dv, int) and dv:
                        hurt[label] = dv
                    if rv != 0:
                        react[label] = rea.strip() if not rea.strip()[0].isdigit() else rv
                rec["damage_tables"].append(dict(table=key, damage=hurt, reaction=react))
        hp = re.findall(r"static CollisionCheckInfoInit2?\s+\w+\s*=\s*\{\s*(\d+)\s*,", src)
        hp += re.findall(r"colChkInfo\.health\s*=\s*(\d+)\s*;", src)
        if hp:
            rec["health"] = sorted({int(x) for x in hp})
        hit_by, deals = [], []
        for fn, t in texts:
            for m in ELEM_RE.finditer(t):
                at_f, _, at_dmg, ac_f, _, _, atelem, acelem = m.groups()
                try:
                    acm, atm = ev(ac_f), ev(at_f)
                except Exception:
                    continue
                if "ACELEM_ON" in acelem and acm:
                    names = decode_flags(acm, dmg_order, dmg_vals)
                    if names not in hit_by:
                        hit_by.append(names)
                if "ATELEM_ON" in atelem and atm:
                    try:
                        dmg = int(at_dmg.strip(), 0)
                    except ValueError:
                        dmg = at_dmg.strip()
                    entry = dict(damage_to_link=dmg, types=decode_flags(atm, dmg_order, dmg_vals))
                    if entry not in deals:
                        deals.append(entry)
        if hit_by:
            rec["can_be_hit_by"] = hit_by
        if deals:
            rec["attacks"] = deals
        if rec:
            rec["file"] = f"src/overlays/actors/{d}/"
            out[actor] = rec
    return out


def song_buttons(root):
    src = _read(root, SONGS)
    body = _block(src, "gOcarinaSongButtons")
    out = {}
    for name, btns in re.findall(r"//\s*(OCARINA_SONG_\w+)\s*\{\s*\d+,\s*\{(.*?)\}", body, re.S):
        out[name] = [b.replace("OCARINA_BTN_", "") for b in re.findall(r"OCARINA_BTN_\w+", btns)]
    return out


def game_rules(root):
    dmg_vals, dmg_order, ev = dmg_constants(root)
    row_names = damage_row_names(root)
    inv, kal, ply, item_h = (_read(root, p) for p in (INV, KALEIDO, PLAYER, ITEM_H))
    items = [n for _, n in enum_list(item_h, "ITEM_")]
    caps = {k: [int(x) for x in v.split(",")] for v, k in re.findall(r"\{\s*([\d,\s]+?)\s*\},\s*//\s*(UPG_\w+)", _block(inv, "gUpgradeCapacities"))}
    spell_costs = [int(x) for x in re.search(r"sMagicSpellCosts\[\]\s*=\s*\{([^}]*)\}", ply).group(1).split(",")]
    arrow_costs = [int(x) for x in re.search(r"sMagicArrowCosts\[\]\s*=\s*\{([^}]*)\}", ply).group(1).split(",")]
    ia = [n for _, n in enum_list(_read(root, os.path.join("include", "player.h")), "PLAYER_IA_")]
    s15 = ia.index("PLAYER_IA_MAGIC_SPELL_15")
    melee = re.search(r"static u32 D_80854488\[\]\[2\]\s*=\s*\{(.*?)\};", ply, re.S).group(1)
    melee_rows = re.findall(r"\{\s*(DMG_\w+),\s*(DMG_\w+)\s*\}", melee)
    hook = _read(root, HOOK)
    hook_len = re.search(r"\?\s*(\d+)\s*:\s*(\d+);", hook).groups()
    hook_speed = re.search(r"Actor_SetProjectileSpeed\(&this->actor,\s*([\d.]+)f\)", hook).group(1)
    return dict(
        sources={k: v.replace(os.sep, "/") for k, v in dict(
            item_slots=INV, age_requirements=KALEIDO, item_actions=PLAYER, capacities=INV, magic_costs=PLAYER,
            melee_damage_flags=PLAYER, damage_tables=BTLTBLS + " + each actor's .c", damage_bits=COLCHK_H, songs=SONGS,
            hookshot=HOOK).items()},
        items=items,
        item_slots=dict(commented_table(inv, "gItemSlots")),
        item_age=dict(commented_table(kal, "gItemAgeReqs")),
        slot_age=dict(commented_table(kal, "gSlotAgeReqs")),
        equip_age=[[v, k] for k, v in commented_table(kal, "gEquipAgeReqs")],
        item_actions=dict(commented_table(ply, "sItemActions")),
        upgrade_capacities=caps,
        magic_spell_costs={ia[s15 + i].replace("PLAYER_IA_", ""): c for i, c in enumerate(spell_costs)},
        magic_arrow_costs=dict(zip(["ARROW_FIRE", "ARROW_ICE", "ARROW_LIGHT"], arrow_costs)),
        melee_damage_flags=dict(zip(["Master Sword", "Kokiri Sword (also the broken Giant's Knife)", "Giant's Knife / Biggoron's Sword",
                                     "Deku Stick", "Megaton Hammer"], [dict(swing=a, jump_attack=b) for a, b in melee_rows])),
        hookshot=dict(flight_frames=dict(hookshot=int(hook_len[0]), longshot=int(hook_len[1])), speed=float(hook_speed)),
        damage_bits={k: f"{dmg_vals[k]:#010x}" for k in dmg_order},
        damage_row_names=row_names,
        songs=song_buttons(root),
        actors=actor_rules(root, dmg_vals, dmg_order, ev, row_names),
    )
