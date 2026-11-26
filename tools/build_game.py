"""Write ootmap/game.json and ootmap/GAME_GUIDE.md: how the whole game fits together.

- what every item, song and piece of equipment does, how to use it, at which age, ammo, magic cost, damage
- the original game replayed through the logic, sphere by sphere: what each step makes possible
- for every key item and event, everything that strictly needs it ("what unlocks what"), and the reverse:
  for every location, the key items and events it strictly needs
- the main story in order, trade quests, enemies (health, what hurts them), what each object can be hit by,
  every ocarina spot in the ROM, and how to equip things in the pause menu

usage: python -I build_game.py <tools_dir> <data/meta> <out_dir>
"""
import collections
import glob
import json
import os
import re
import sys

TOOLS, META, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
ROOT = os.path.dirname(os.path.abspath(TOOLS))
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(ROOT, "ootmap"))
import game_knowledge as K  # noqa: E402
import logic_eval as LE  # noqa: E402

GOAL = "Ganon"
NON_ITEMS = {"Event", "Drop", "HintStone", "Hint"}
JUNK = re.compile(r"^(Rupee|Rupees|Recovery Heart|Arrows \(|Bombs \(|Bomb \(|Deku Nuts \(|Deku Seeds|Deku Stick \(|Nothing|"
                  r"Buy |Fairy|Bombchus \(|Ice Trap|Milk$|Fish$|Bugs$|Deku Nut Drop|Deku Stick Drop|Map \(|Compass \()")
SONG_KEYS = {"Minuet": "OCARINA_SONG_MINUET", "Bolero": "OCARINA_SONG_BOLERO", "Serenade": "OCARINA_SONG_SERENADE",
             "Requiem": "OCARINA_SONG_REQUIEM", "Nocturne": "OCARINA_SONG_NOCTURNE", "Prelude": "OCARINA_SONG_PRELUDE"}


def jload(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return json.load(f)


def logic_item(vanilla):
    """What a vanilla location's item adds to the evaluator's inventory."""
    return "Magic Bean x10" if vanilla == "Buy Magic Bean" else vanilla  # the bean seller sells ten


class Memo:
    """Cache rule results until something they can depend on changes (items, events, reached regions, pass)."""
    _ver = 0
    _pass = 0

    def rule(self, text, age):
        ver = (len(self.collected), self._ver, self._pass, self._reached_ver())
        if getattr(self, "_memo_ver", None) != ver:
            self._memo, self._memo_ver = {}, ver
        key = (text, age)
        if key not in self._memo:
            self._memo[key] = super().rule(text, age)
        return self._memo[key]

    def _reached_ver(self):
        return len(self.reached)


class Blocked(Memo, LE.Logic):
    """The evaluator with some items/events forced off, to see what strictly needs them."""

    def __init__(self, items, blocked=(), **kw):
        super().__init__(items, **kw)
        self.blocked = set(blocked)

    def count(self, ident):
        return 0 if ident in self.blocked else super().count(ident)

    def has_bottle(self):
        return False if "Bottle" in self.blocked else super().has_bottle()


class Collector(Memo, LE.Logic):
    """One fixpoint that walks regions AND picks up every location's original item as soon as its rule holds.
    With `caps` it plays the game with an item capped (0 = never found), which answers "what can't you get
    without X" including everything that sits behind X."""

    def __init__(self, items, caps=None, **kw):
        super().__init__(items, **kw)
        self.caps = caps or {}
        self.fast = True

    def count(self, ident):
        n = super().count(ident)
        cap = self.caps.get(ident[4:] if ident.startswith("Buy_") else ident)  # capping an item also caps buying it
        return n if cap is None else min(n, cap)

    def has_bottle(self):
        return False if self.caps.get("Bottle") == 0 else super().has_bottle()

    def _reached_ver(self):
        return 0  # a new pass starts whenever regions were added, so within a pass reached-staleness is harmless

    def add(self, raw):
        self._ver += 1
        n, m = 1, re.match(r"(.*?)\s*[x\*:]\s*(\d+)$", raw)
        if m:
            raw, n = m.group(1), int(m.group(2))
        e = LE.escape(raw)
        if e in LE.ALIASES:
            ident, c = LE.ALIASES[e]
            self.inv[ident] = max(self.inv.get(ident, 0), c)
        else:
            self.inv[e] = self.inv.get(e, 0) + n

    def solve_all(self, by_region, item_of):
        self.got, changed = set(), True
        self.reached = {("Root", "child"), ("Root", "adult")}
        order = list(self.reached)
        while changed:
            changed = False
            self._pass += 1
            i = 0
            while i < len(order):  # regions reached during this pass are handled in this pass too
                region, age = order[i]
                i += 1
                r = self.regions.get(region)
                if not r:
                    continue
                for ev_name, rl in r["events"].items():
                    e = LE.escape(ev_name)
                    if e not in self.collected and self.rule(rl, age)[0]:
                        self.collected.add(e)
                        changed = True
                for ln, rl in r["locations"].items():
                    loc = self.locations.get(ln)
                    if loc and loc["type"] in self.AUTO and loc.get("vanilla_item"):
                        e = LE.escape(loc["vanilla_item"])
                        if e not in self.collected and self.rule(rl, age)[0]:
                            self.collected.add(e)
                            changed = True
                if self._age_live(age):
                    for ln in by_region.get(region, ()):
                        if ln not in self.got and self.rule(self.locations[ln].get("logic_rule") or "True", age)[0]:
                            self.got.add(ln)
                            self.add(item_of[ln])
                            changed = True
                for ex in r["exits"]:
                    st = (ex["to"], age)
                    if st not in self.reached and self.rule(ex["rule"], age)[0]:
                        self.reached.add(st)
                        order.append(st)
                        changed = True
        return self


def in_logic(L, names):
    return {n for n in names if L.location_status(n, explain=False)["status"] == "in_logic"}


def live_regions(L):
    return {(r, a) for (r, a) in L.reached if L._age_live(a)}


def main():
    items_db = jload(OUT, "items.json")
    locs = {i["name"]: i for i in items_db}
    graph = jload(OUT, "logic", "world_graph.json")["regions"]
    helpers = jload(OUT, "logic", "helpers.json")
    rules = jload(META, "game_rules.json")
    decomp = jload(META, "decomp.json")
    event_names = sorted({k for r in graph for k in r["events"]})
    event_region = {}
    for r in graph:
        for k, v in r["events"].items():
            event_region.setdefault(k, []).append(dict(region=r["region"], rule=v))
    checkable = [n for n, l in locs.items() if l.get("region") and l.get("vanilla_item") and (l["type"] not in NON_ITEMS or l["type"] == "Event")]  # Event: Ganon, Pierre, Ruto's letter, Time Travel
    words = set()
    for text in [e["rule"] for r in graph for e in r["exits"]] + [v for r in graph for v in r["locations"].values()] + \
            [v for r in graph for v in r["events"].values()] + list(helpers.values()) + list(helpers.keys()):
        words |= set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text))
    def progression(v):
        lv = logic_item(v or "")
        return bool(v) and not JUNK.match(lv) and (LE.escape(lv.split(" x")[0]) in words or lv == "Triforce"
                                                   or lv.startswith(("Small Key", "Boss Key", "Silver Rupee")))
    key_checks = [n for n in checkable if progression(locs[n]["vanilla_item"])]
    tricks_all = sorted({w for w in words if w.startswith("logic_")})
    mk = lambda inv, tr=(), bl=(): Blocked(list(inv), blocked=bl, tricks=list(tr), data_dir=OUT).solve()  # noqa: E731
    by_region = collections.defaultdict(list)
    for n in checkable:
        by_region[locs[n]["region"]].append(n)
    item_of = {n: logic_item(locs[n]["vanilla_item"]) for n in checkable}
    play = lambda start, tr, caps=None: Collector(list(start), caps=caps, tricks=list(tr), data_dir=OUT).solve_all(by_region, item_of)  # noqa: E731

    def fixpoint(start, tr):
        return play(start, tr).got

    dungeon_keys = sorted({locs[n]["vanilla_item"] for n in key_checks if locs[n]["vanilla_item"].startswith("Small Key (")})

    def pick_unstick(L, inv0, tr, got0):
        """Standard logic is stuck. Candidates: the tricks the logic names as alternatives for the key items still
        missing, and one more small key for a dungeon (the randomizer's key rules count keys for the worst case, a
        random layout; the original layout opens its doors in a fixed order). Keep the one that lets the original
        layout get furthest; on a tie prefer the trick."""
        cands = set()
        for n in key_checks:
            if n not in got0:
                cands |= {("trick", t) for t in re.findall(r"trick: (logic_\w+)", json.dumps(L.location_status(n)))}
        cands |= {("key", k) for k in dungeon_keys}
        best, best_key = None, None
        for kind, x in sorted(cands):
            reach = fixpoint(extra_keys + [x], tr) if kind == "key" else fixpoint(extra_keys, tr + [x])
            score = (len([n for n in reach if n in key_set]), len(reach), kind == "trick")
            if len(reach) > len(got0) and (best_key is None or score > best_key):
                best, best_key = (kind, x), score
        return best

    key_set = set(key_checks)
    # ---------------------------------------------------------------- 1. the original game, sphere by sphere
    inv, got, spheres, tricks, goal_sphere, extra_keys = [], {}, [], [], None, []
    seen_regions, seen_events = set(), set()
    while True:
        L = mk(inv, tricks)
        new = sorted(in_logic(L, [n for n in checkable if n not in got]))
        regions = live_regions(L)
        events = {e for e in event_names if L.count(LE.escape(e))}
        if not new:
            if GOAL in got:
                goal_sphere = got[GOAL]
                break
            best = pick_unstick(L, inv, tricks, got)
            if not best:
                print("stuck; goal status:", json.dumps(L.location_status(GOAL))[:600])
                break
            if best[0] == "trick":
                tricks.append(best[1])
                spheres.append(dict(sphere=len(spheres), kind="trick_needed", trick=best[1],
                                    note="Standard logic can't go further with the original item layout. The randomizer files "
                                         "this move under a trick, but the original game's route needs it here."))
            else:
                inv.append(best[1])
                extra_keys.append(best[1])
                spheres.append(dict(sphere=len(spheres), kind="key_rule_relaxed", key=best[1],
                                    note="The randomizer's key rules count keys for the worst case (keys spent on other doors "
                                         "first, which a random layout allows). With the original layout these doors open in a "
                                         "fixed order, so one more key is counted for this dungeon from here on."))
            continue
        idx = len(spheres)
        for n in new:
            got[n] = idx
            inv.append(logic_item(locs[n]["vanilla_item"]))
        spheres.append(dict(
            sphere=idx, kind="items",
            key_items=[dict(item=locs[n]["vanilla_item"], location=n, region=locs[n]["region"]) for n in new if progression(locs[n]["vanilla_item"])],
            other_locations=len([n for n in new if not progression(locs[n]["vanilla_item"])]),
            new_events=sorted(events - seen_events),
            new_regions=sorted({f"{r} ({a})" for r, a in regions - seen_regions}),
        ))
        seen_regions |= regions
        seen_events |= events
    final = play(extra_keys, tricks)
    base_locs = set(final.got)
    base_regions = live_regions(final)
    ev_of = lambda L_: {e for e in event_names if L_.count(LE.escape(e))}  # noqa: E731
    base_events = ev_of(final)
    assert base_locs == set(got), (len(base_locs), len(got))
    print(f"playthrough: {len(spheres)} steps, {len(got)} locations, goal in logic after sphere: {goal_sphere}, tricks: {tricks}")

    # ---------------------------------------------------------------- 2. what strictly needs each key item / event
    tested = []
    counts = collections.Counter(LE.escape(x.split(" x")[0]) for x in inv if x not in extra_keys)
    for v in sorted({locs[n]["vanilla_item"] for n in got if progression(locs[n]["vanilla_item"])}):
        ident = LE.escape(logic_item(v).split(" x")[0])
        tested.append((v, ident, "all"))
        if counts[ident] > 1 and not v.startswith(("Small Key", "Silver Rupee", "Gold Skulltula", "Piece of Heart", "Heart Container")):
            tested.append((v, ident, "last"))
    required_for, needs = {}, collections.defaultdict(list)
    for v, ident, mode in tested + [(e, LE.escape(e), "event") for e in event_names]:
        cap = counts[ident] - 1 if mode == "last" else 0
        L2 = play(extra_keys, tricks, caps={ident: cap})
        label = f"{v} (the last of {counts[ident]})" if mode == "last" else (f"event: {v}" if mode == "event" else v)
        lost = sorted(base_locs - L2.got)
        lost_regions = sorted({r for r, a in base_regions - live_regions(L2)})
        lost_events = sorted(base_events - ev_of(L2) - ({v} if mode == "event" else set()))
        if not lost and not lost_regions and not lost_events:
            continue
        required_for[label] = dict(
            locations=len(lost), key_items_behind_it=sorted({locs[n]["vanilla_item"] for n in lost if progression(locs[n]["vanilla_item"])}),
            events=lost_events, regions=lost_regions, location_names=lost)
        for n in lost:
            needs[n].append(label)
        for e in lost_events:
            needs["event:" + e].append(label)
    print(f"required_for: {len(required_for)} items/events with something behind them")
    providers = collections.defaultdict(list)
    for n in got:
        providers[locs[n]["vanilla_item"]].append(n)
    for n, l in locs.items():  # shops sell some key items (Deku Shield, Hylian Shield); a shop needs nothing extra here
        if (l.get("vanilla_item") or "").startswith("Buy ") and l.get("region") in {r for r, a in base_regions}:
            providers[l["vanilla_item"][4:]].append(n)

    def req_of(label):
        if label.startswith("event: "):
            return set(needs.get("event:" + label[7:], []))
        m = re.match(r"(.*) \(the last of \d+\)$", label)
        ps = sorted(providers.get(m.group(1), []), key=lambda n: got[n])[-1:] if m else providers.get(label, [])
        sets = [set(needs.get(p, [])) for p in ps]
        return set.intersection(*sets) if sets else set()

    def direct(labels):
        labels = set(labels)
        implied = set().union(*(req_of(a) for a in labels)) if labels else set()
        return sorted(labels - implied)
    direct_needs = {n: direct(v) for n, v in needs.items()}
    for label, rec in required_for.items():
        du = sorted((n for n, d in direct_needs.items() if label in d),
                    key=lambda n: (not n.startswith("event:"), not progression(locs.get(n, {}).get("vanilla_item")), n))
        rec["directly_unlocks"] = [dict(event=n[6:]) if n.startswith("event:") else
                                   dict(location=n, item=locs[n]["vanilla_item"]) for n in du]

    # ---------------------------------------------------------------- 3. items catalog
    slots = rules["item_slots"]
    upg_for = {"ITEM_DEKU_STICK": "UPG_DEKU_STICKS", "ITEM_DEKU_NUT": "UPG_DEKU_NUTS", "ITEM_BOMB": "UPG_BOMB_BAG",
               "ITEM_BOW": "UPG_QUIVER", "ITEM_SLINGSHOT": "UPG_BULLET_BAG", "ITEM_ADULTS_WALLET": "UPG_WALLET",
               "ITEM_GIANTS_WALLET": "UPG_WALLET", "ITEM_BOMB_BAG_20": "UPG_BOMB_BAG", "ITEM_QUIVER_30": "UPG_QUIVER",
               "ITEM_BULLET_BAG_30": "UPG_BULLET_BAG"}
    magic = {**{"ITEM_" + k: v for k, v in rules["magic_arrow_costs"].items()},
             **{"ITEM_" + k: v for k, v in rules["magic_spell_costs"].items() if not k.startswith("MAGIC_SPELL")}}
    melee = {"ITEM_SWORD_KOKIRI": "Kokiri Sword (also the broken Giant's Knife)", "ITEM_SWORD_MASTER": "Master Sword",
             "ITEM_SWORD_BIGGORON": "Giant's Knife / Biggoron's Sword", "ITEM_GIANTS_KNIFE": "Giant's Knife / Biggoron's Sword",
             "ITEM_DEKU_STICK": "Deku Stick", "ITEM_HAMMER": "Megaton Hammer"}
    hook = rules["hookshot"]
    reach = {k: round(v * hook["speed"] * 1.5) for k, v in hook["flight_frames"].items()}
    age_word = {"AGE_REQ_CHILD": "child", "AGE_REQ_ADULT": "adult", "AGE_REQ_NONE": "both"}
    found_at = collections.defaultdict(list)
    for n, l in locs.items():
        if l.get("vanilla_item"):
            found_at[l["vanilla_item"]].append(n)
    catalog = []
    for key, (name, rname, use, does) in K.ITEMS.items():
        rec = dict(item=key, name=name, use=use, does=does, curated=True)
        if key in slots:
            s = slots[key]
            si = list(rules["slot_age"]).index(s)
            rec.update(slot=s, slot_index=si, menu_row=si // 6, menu_col=si % 6)
        age = rules["item_age"].get(key)
        if age:
            rec["usable_by"] = age_word.get(age, age)
        if key in rules["item_actions"]:
            rec["player_item_action"] = rules["item_actions"][key]
        if key in upg_for:
            rec["capacity_by_upgrade_level"] = rules["upgrade_capacities"][upg_for[key]]
        if key in magic:
            rec["magic_cost"] = magic[key]
        if key in melee:
            rec["damage_flags"] = rules["melee_damage_flags"][melee[key]]
        if key in ("ITEM_HOOKSHOT", "ITEM_LONGSHOT"):
            w = "hookshot" if key == "ITEM_HOOKSHOT" else "longshot"
            rec["reach_units"] = reach[w]
            rec["reach_note"] = f"{hook['flight_frames'][w]} frames x speed {hook['speed']:g} x 1.5 (z_arms_hook.c)"
        if rname:
            rec["randomizer_name"] = rname
            fa = found_at.get(rname, []) + found_at.get("Buy " + rname, [])
            rec["found_at"] = [dict(location=n, sphere=got.get(n)) for n in sorted(fa, key=lambda n: (got.get(n, 99), n))]
            rf = {k: dict(v, location_names=None) for k, v in required_for.items() if k == rname or k.startswith(rname + " (")}
            if rf:
                rec["strictly_needed_for"] = {k: {kk: vv for kk, vv in v.items() if vv is not None} for k, v in rf.items()}
        catalog.append(rec)

    # ---------------------------------------------------------------- 4. songs
    songs = []
    for key, (name, rname, effect) in K.SONGS.items():
        rec = dict(song=key, name=name, effect=effect, curated=True, notes=rules["songs"].get(key))
        rec["learned_at"] = [dict(location=n, sphere=got.get(n)) for n in found_at.get(rname, [])]
        if rname in required_for:
            rec["strictly_needed_for"] = {rname: {k: v for k, v in required_for[rname].items() if k != "location_names"}}
        songs.append(rec)

    # ---------------------------------------------------------------- 5. actors in the world: enemies and objects
    placements = collections.defaultdict(lambda: collections.Counter())
    ocarina_spots, time_blocks = [], []
    for p in sorted(glob.glob(os.path.join(OUT, "scenes", "[0-9]*_*.json"))):
        sc = jload(p)
        for room in sc["rooms"]:
            for layer, lay in room["layers"].items():
                for a in lay["actors"]:
                    placements[a["actor"]][sc["enum"]] += 1
                    d = a.get("decoded") or {}
                    if d.get("kind") == "ocarina_spot" and d.get("play"):
                        ocarina_spots.append(dict(scene=sc["enum"], room=room["room"], layer=layer, pos=a["pos"], **d))
                    if d.get("kind") == "song_of_time_block":
                        time_blocks.append(dict(scene=sc["enum"], room=room["room"], layer=layer, pos=a["pos"]))
    dedup = {}
    for o in ocarina_spots:
        dedup.setdefault((o["scene"], o["room"], tuple(o["pos"]), o["play"]), dict(o, layers=[]))["layers"].append(o["layer"])
    ocarina_spots = [dict({k: v for k, v in o.items() if k != "layer"}) for o in dedup.values()]
    typical = collections.defaultdict(collections.Counter)
    actors = {}
    for name, rec in rules["actors"].items():
        r = dict(rec)
        r["description"] = decomp["actor_descriptions"].get(name)
        if name in placements:
            r["placed_in_rom"] = dict(total=sum(placements[name].values()), scenes=sorted(placements[name]))
        for t in r.get("damage_tables", []):
            for row, dmg in t["damage"].items():
                typical[row][dmg] += 1
            for row, rv in list(t["reaction"].items()):
                if isinstance(rv, str):
                    m = re.search(r"(?:REACT|DMGEFF|DMG_EFF|EFF|DE|DAMAGE_EFFECT|DMG)_(\w+)$", rv)
                    t["reaction"][row] = dict(code=rv, meaning=(m.group(1) if m else rv).lower().replace("_", " "))
        actors[name] = r
    typical_damage = {row: dict(most_common=c.most_common(1)[0][0], seen=dict(sorted(c.items()))) for row, c in typical.items()}

    # ---------------------------------------------------------------- 6. main quest, with the logic's verdict
    def check_info(c):
        if c.startswith("event:"):
            e = c[6:]
            sph = next((s["sphere"] for s in spheres if s.get("kind") == "items" and e in s["new_events"]), None)
            return dict(check=c, sphere=sph, where=[x["region"] for x in event_region.get(e, [])],
                        directly_needs=direct_needs.get(c, []), strictly_needs=sorted(needs.get(c, [])))
        assert c in locs, f"main quest check {c!r} is not a location"
        return dict(check=c, sphere=got.get(c), where=locs.get(c, {}).get("region"),
                    vanilla_item=locs.get(c, {}).get("vanilla_item"),
                    directly_needs=direct_needs.get(c, []), strictly_needs=sorted(needs.get(c, [])))
    main_quest = [dict(step=i + 1, title=t, how=h, curated=True, checks=[check_info(c) for c in cs]) for i, (t, cs, h) in enumerate(K.MAIN_QUEST)]

    events = [dict(event=e, set_in=event_region[e], sphere=next((s["sphere"] for s in spheres if s.get("kind") == "items" and e in s["new_events"]), None),
                   strictly_needed_for={k: v for k, v in required_for.get(f"event: {e}", {}).items() if k != "location_names"} or None)
              for e in event_names]

    out = dict(
        about=("How the whole game fits together, for bots. Numbers come from the game code (data/meta/game_rules.json, "
               "read from the zeldaret/oot decomp) or the ROM. Text marked curated=true is hand-written. 'Spheres' and "
               "'strictly needed' come from replaying the original item layout through the randomizer's standard "
               "(glitchless) logic: 'strictly needed' means standard logic has no other way; speedrun tricks and glitches "
               "may still get there without it."),
        sources=rules["sources"],
        units=dict(damage_to_link="health units: 16 = 1 heart, before Double Defense halves it (Health_ChangeBy)",
                   enemy_health="hit points in the actor's colChkInfo; each hit removes the damage-table value",
                   magic="magic units: one magic bar = 48, the upgraded bar = 96"),
        menus=K.MENUS,
        items=catalog,
        songs=songs,
        main_quest=main_quest,
        playthrough=dict(note="Every location that is in standard logic is collected each sphere. A sphere lists the key items "
                              "it adds; the next sphere is what they open.", tricks_needed=tricks, spheres=spheres,
                         extra_keys_counted=extra_keys, goal=GOAL, goal_in_logic_after_sphere=goal_sphere),
        strictly_needed_for=dict(sorted(required_for.items())),
        location_needs={n: dict(directly=direct_needs[n], all=sorted(v)) for n, v in sorted(needs.items())},
        events=events,
        trade_quests=K.TRADE_QUESTS,
        combat=dict(attack_types=rules["damage_row_names"], damage_bits=rules["damage_bits"],
                    melee_weapon_damage_flags=rules["melee_damage_flags"],
                    typical_damage_per_attack=typical_damage,
                    how_damage_works=("A hit's damage type is one bit (damage_bits). If the target has a damage table, the table "
                                      "row for that bit gives damage (low 4 bits) and a reaction code (high 4 bits); reaction "
                                      "codes are the actor's own (stun, fire, freeze...). Without a table the attack's own "
                                      "damage minus the target's defense is used, and the actor's code decides what happens "
                                      "(most bosses work this way). can_be_hit_by lists what each collider accepts at all.")),
        actors=actors,
        ocarina_spots=ocarina_spots,
        song_of_time_blocks=time_blocks,
    )
    with open(os.path.join(OUT, "game.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    write_guide(out, os.path.join(OUT, "GAME_GUIDE.md"))
    print("wrote game.json and GAME_GUIDE.md")


MINOR = re.compile(r"^(Gold Skulltula Token|Small Key|Boss Key|Silver Rupee|Piece of Heart|Heart Container)")


def write_guide(g, path):
    L = []
    w = L.append
    w("# How Ocarina of Time fits together")
    w("")
    w("What every item does, what each task unlocks, and the order the original game is played in. Generated by")
    w("`tools/build_game.py`; bots should read `game.json` (same data, plus every location name).")
    w("")
    w("- **Curated** text is hand-written. Numbers (ammo, magic, age limits, damage, hookshot reach) come from the game code.")
    w("- **Spheres** come from replaying the original item layout through the randomizer's standard logic: sphere 0 is")
    w("  what you can get at the start, sphere N+1 is what sphere N's items open.")
    w("- **Strictly needed** means standard (glitchless) logic has no other way: the game was replayed from the start")
    w("  without that item or event, and these things stayed out of logic. Speedrun tricks and glitches may still get")
    w("  there without it, so this is never a claim that something is unreachable. **Directly needs** drops anything")
    w("  that another item on the list already needs (Light Arrows imply the Master Sword, and so on).")
    w("")
    w("## Main quest")
    w("")
    for s in g["main_quest"]:
        w(f"### {s['step']}. {s['title']}")
        w("")
        w(s["how"])
        w("")
        for c in s["checks"]:
            nm = c["check"].replace("event:", "event: ")
            needs = ", ".join(c["directly_needs"]) or "nothing beyond reaching it"
            item = f" → {c['vanilla_item']}" if c.get("vanilla_item") else ""
            w(f"- `{nm}`{item} (sphere {c['sphere']}). Directly needs: {needs} ({len(c['strictly_needs'])} things in all).")
        w("")
    P = g["playthrough"]
    w("## The original game, sphere by sphere")
    w("")
    w(P["note"] + f" The goal (`{P['goal']}`, beating Ganon) is beaten in sphere {P['goal_in_logic_after_sphere']}."
      if P["goal_in_logic_after_sphere"] is not None else P["note"] + " Standard logic did not reach the goal.")
    if P["tricks_needed"] or P["extra_keys_counted"]:
        w(f"Standard logic got stuck {len(P['tricks_needed']) + len(P['extra_keys_counted'])} time(s) with the original layout. "
          "Each time, the step that lets the original route continue is turned on and marked below.")
    w("")
    for s in P["spheres"]:
        if s["kind"] == "trick_needed":
            w(f"- **Sphere {s['sphere']}: trick needed:** `{s['trick']}`. {s['note']}")
            continue
        if s["kind"] == "key_rule_relaxed":
            w(f"- **Sphere {s['sphere']}: one more {s['key']} counted.** {s['note']}")
            continue
        major = [k for k in s["key_items"] if not MINOR.match(k["item"])]
        minor = collections.Counter(MINOR.match(k["item"]).group(1) for k in s["key_items"] if MINOR.match(k["item"]))
        ki = "; ".join(f"{k['item']} ({k['location']})" for k in major) or "no major items"
        mi = ", ".join(f"{n} {kind}" for kind, n in sorted(minor.items()))
        ev = f" Events: {', '.join(s['new_events'])}." if s["new_events"] else ""
        w(f"- **Sphere {s['sphere']}:** {ki}." + (f" Also {mi}." if mi else "") + f" Plus {s['other_locations']} other locations.{ev}")
    w("")
    w("## What unlocks what")
    w("")
    w("For each key item and event: how many locations are out of standard logic without it (everything behind it, however")
    w("deep), and what it **directly** unlocks: the checks where it is an immediate requirement.")
    w("")
    w("| Item or event | Locations behind it | Directly unlocks |")
    w("|---|---|---|")
    for k, v in sorted(g["strictly_needed_for"].items(), key=lambda kv: -kv[1]["locations"]):
        du = v.get("directly_unlocks", [])
        named = [f"event {d['event']}" if "event" in d else f"{d['item']} ({d['location']})" for d in du
                 if "event" in d or not (JUNK.match(d["item"]) or MINOR.match(d["item"]))]
        rest = len(du) - len(named)
        cell = "; ".join(named[:10]) + (f"; +{len(named) - 10} more" if len(named) > 10 else "") + (f" (+{rest} minor)" if rest else "")
        w(f"| {k} | {v['locations']} | {cell or '-'} |")
    w("")
    w("## Items")
    w("")
    w("| Item | Use | Age | What it does | Ammo / magic / reach | First found (sphere) |")
    w("|---|---|---|---|---|---|")
    for it in g["items"]:
        extra = []
        if it.get("capacity_by_upgrade_level"):
            extra.append("capacity " + "/".join(str(x) for x in it["capacity_by_upgrade_level"] if x))
        if it.get("magic_cost"):
            extra.append(f"magic {it['magic_cost']}")
        if it.get("reach_units"):
            extra.append(f"reach {it['reach_units']} units")
        fa = it.get("found_at") or []
        first = f"{fa[0]['location']} ({fa[0]['sphere']})" if fa else ""
        w(f"| {it['name']} | {it['use']} | {it.get('usable_by', '')} | {it['does']} | {', '.join(extra)} | {first} |")
    w("")
    w("## Songs")
    w("")
    w("| Song | Notes | What it does | Learned at (sphere) |")
    w("|---|---|---|---|")
    for s in g["songs"]:
        notes = " ".join((s["notes"] or [])) if s["notes"] else "you compose it"
        la = ", ".join(f"{x['location']} ({x['sphere'] if x['sphere'] is not None else 'not in the replay'})" for x in s["learned_at"])
        w(f"| {s['name']} | {notes} | {s['effect']} | {la} |")
    w("")
    w(f"Ocarina spots in the ROM: {len(g['ocarina_spots'])} (`ocarina_spots` in game.json: scene, room, position, song, effect, switch flag).")
    w(f"Song of Time blocks: {len(g['song_of_time_blocks'])} placements.")
    w("")
    w("## Trade quests")
    w("")
    for age, chain in g["trade_quests"].items():
        w(f"- **{age.capitalize()}:** " + " → ".join(chain))
    w("")
    w("## Pause menu: equipping things")
    w("")
    for k, v in g["menus"].items():
        w(f"- **{k.replace('_', ' ')}:** {v}")
    w("")
    w("## Combat")
    w("")
    w(g["combat"]["how_damage_works"])
    w("")
    w("Typical damage per attack type (the most common value across all enemy damage tables):")
    w("")
    w("| Attack | Usual damage | Values seen (count) |")
    w("|---|---|---|")
    for row in g["combat"]["attack_types"]:
        t = g["combat"]["typical_damage_per_attack"].get(row)
        if t:
            w(f"| {row} | {t['most_common']} | " + ", ".join(f"{k}: {v}" for k, v in t["seen"].items()) + " |")
    w("")
    w("Swords and other melee weapons pick their damage type like this (z_player.c):")
    w("")
    for k, v in g["combat"]["melee_weapon_damage_flags"].items():
        w(f"- **{k}:** swing `{v['swing']}`, jump attack `{v['jump_attack']}`")
    w("")
    w("## Enemies (actors with a damage table that some attack hurts, placed in the ROM)")
    w("")
    w("Bosses and some enemies have no damage table: their own code decides what hurts them (see `can_be_hit_by` and the")
    w("main quest notes). Reaction numbers are the actor's own codes; named ones are decoded from the actor's enum.")
    w("")
    w("| Actor | What it is | Health | Immune to | Reactions |")
    w("|---|---|---|---|---|")
    rows = g["combat"]["attack_types"]
    for name, a in sorted(g["actors"].items()):
        if not a.get("damage_tables") or not a.get("placed_in_rom") or not any(a["damage_tables"][0]["damage"].values()):
            continue
        t = a["damage_tables"][0]
        immune = [r for r in rows[:14] if r not in t["damage"] and r not in t["reaction"] and not r.startswith("Unk")]
        react = "; ".join(f"{k}: {v['meaning'] if isinstance(v, dict) else v}" for k, v in list(t["reaction"].items())[:6])
        hp = "/".join(str(x) for x in a.get("health", [])) or "?"
        w(f"| {name} | {a.get('description') or ''} | {hp} | {', '.join(immune) or '-'} | {react} |")
    w("")
    w("Objects that only certain attacks can hit (from their colliders), e.g.:")
    w("")
    shown = 0
    for name, a in sorted(g["actors"].items()):
        if a.get("damage_tables") or not a.get("placed_in_rom") or not a.get("can_be_hit_by"):
            continue
        hb = [x for x in a["can_be_hit_by"] if x and len(x) <= 6 and not x[0].startswith("everything except")]
        if not hb:
            continue
        w(f"- **{name}** ({a.get('description') or 'object'}): " + " | ".join(", ".join(x.replace("DMG_", "").lower() for x in h) for h in hb))
        shown += 1
    w("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    main()
