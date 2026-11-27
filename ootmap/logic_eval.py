"""Basic logic evaluator for the OoT map database (stdlib only).

It answers "with these items, which locations are IN STANDARD LOGIC?" using the randomizer's
glitchless rules with vanilla settings. It never claims a place is unreachable: anything outside
logic is reported as "not_in_standard_logic" together with what the logic would want, because
tricks, glitches and speedrun skips can bypass those requirements.

  python logic_eval.py --items "Kokiri Sword, Deku Shield, Slingshot, Bomb Bag"
  python logic_eval.py --items "..." --location "Deku Tree Slingshot Chest"
  python logic_eval.py --items "..." --scene "Dodongos Cavern" --json
  add --explain to the list/scene views to include what logic wants for every location (slower)
  options: --all-keys (assume every dungeon key/boss key), --tricks all|logic_name,..., --strict (stop on an
           unknown item name instead of warning),
           --glitches (also enable glitch_/adv_ toggles), --hearts N (default 3)

Simplifications (it is "basic"): time of day is treated as always reachable, rupees/wallet
size are ignored, enemy souls are assumed, and at()/here() are approximated. Like the randomizer with
keys in their original places, it counts one free Fire Temple small key.
"""
import ast
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NOTE = ("Standard logic only (glitchless, no tricks unless enabled). Not being in logic does NOT mean "
        "unreachable: tricks, glitches or skips used in speedruns may get there anyway.")


_CACHE = {}


def _load(rel, base=HERE):
    p = os.path.join(base, rel)
    if p not in _CACHE:
        with open(p, encoding="utf-8") as f:
            _CACHE[p] = json.load(f)
    return _CACHE[p]


def escape(name):
    """Randomizer item/event name -> identifier: 'Small Key (Forest Temple)' -> 'Small_Key_Forest_Temple'."""
    return re.sub(r"[^A-Za-z0-9_]", "", str(name).strip().replace(" ", "_").replace("-", "_"))


ALIASES = {  # friendly names -> (identifier, count)
    "Hookshot": ("Progressive_Hookshot", 1), "Longshot": ("Progressive_Hookshot", 2),
    "Goron_Bracelet": ("Progressive_Strength_Upgrade", 1), "Silver_Gauntlets": ("Progressive_Strength_Upgrade", 2),
    "Golden_Gauntlets": ("Progressive_Strength_Upgrade", 3), "Silver_Scale": ("Progressive_Scale", 1),
    "Golden_Scale": ("Progressive_Scale", 2), "Bombs": ("Bomb_Bag", 1), "Magic": ("Magic_Meter", 1),
    "Fairy_Ocarina": ("Ocarina", 1), "Ocarina_of_Time": ("Ocarina", 2), "Adult_Wallet": ("Progressive_Wallet", 1),
    "Giants_Wallet": ("Progressive_Wallet", 2), "Bottle": ("Bottle", 1), "Master_Sword": ("Master_Sword", 1),
    # the in-game names (game.json / GAME_GUIDE.md) -> the randomizer's
    "Fairy_Bow": ("Bow", 1), "Fairy_Slingshot": ("Slingshot", 1), "Fire_Arrow": ("Fire_Arrows", 1),
    "Ice_Arrow": ("Ice_Arrows", 1), "Light_Arrow": ("Light_Arrows", 1), "Empty_Bottle": ("Bottle", 1),
    "Gorons_Bracelet": ("Progressive_Strength_Upgrade", 1), "Adults_Wallet": ("Progressive_Wallet", 1),
    "Broken_Gorons_Sword": ("Broken_Sword", 1), "Eye_Drops": ("Eyedrops", 1), "Biggorons_Sword": ("Biggoron_Sword", 1),
    "Gerudos_Membership_Card": ("Gerudo_Membership_Card", 1), "Gerudo_Card": ("Gerudo_Membership_Card", 1),
    "Kokiris_Emerald": ("Kokiri_Emerald", 1), "Gorons_Ruby": ("Goron_Ruby", 1), "Zoras_Sapphire": ("Zora_Sapphire", 1),
    "Scarecrows_Song": ("Scarecrow_Song", 1), "Deku_Stick_upgrade": ("Deku_Stick_Capacity", 1),
    "Deku_Nut_upgrade": ("Deku_Nut_Capacity", 1), "Bomb": ("Bomb_Bag", 1), "Cucco": ("Chicken", 1),
    "Bottle_with_Letter": ("Rutos_Letter", 1), "Bottle_with_Rutos_Letter": ("Rutos_Letter", 1),
    "Red_Potion": ("Bottle_with_Red_Potion", 1), "Green_Potion": ("Bottle_with_Green_Potion", 1),
    "Blue_Potion": ("Bottle_with_Blue_Potion", 1), "Bottled_Fairy": ("Bottle_with_Fairy", 1),
    "Lon_Lon_Milk": ("Bottle_with_Milk", 1), "Half_Lon_Lon_Milk": ("Bottle_with_Milk", 1), "Bug": ("Bottle_with_Bugs", 1),
    "Poe": ("Bottle_with_Poe", 1), "Big_Poe": ("Bottle_with_Big_Poe", 1),
    # the bean seller sells ten; can_plant_bean wants (Magic_Bean, 10)
    "Magic_Beans": ("Magic_Bean", 10), "Magic_Bean_Pack": ("Magic_Bean", 10), "Buy_Magic_Bean": ("Magic_Bean", 10),
}
# Things a bot may list that the logic never looks at (always owned, or handled automatically). Accepted quietly.
NO_EFFECT = {"Kokiri_Tunic", "Kokiri_Boots", "Bullet_Bag", "Quiver", "Deku_Stick", "Deku_Sticks", "Deku_Nut", "Deku_Nuts",
             "Bombchu", "Compass", "Dungeon_Map", "Map", "Recovery_Heart", "Rupee", "Rupees", "Arrows", "Deku_Seeds"}
NEEDS_DUNGEON = {"Small_Key", "Boss_Key", "Silver_Rupee"}
ITEM_HELPER_NAMES = {"Hookshot", "Longshot", "Silver_Gauntlets", "Golden_Gauntlets", "Bombs"}
# With keys in their original places the randomizer starts you with one extra Fire Temple key (ItemPool.py: its
# key rules assume a key could be spent on the locked door near the boss key). Mirror that so vanilla works.
FREE_KEYS = {"Small_Key_Fire_Temple": 1}
# Unless notes are shuffled, the randomizer gives every ocarina button at the start (ItemPool.py,
# "if not world.settings.shuffle_individual_ocarina_notes": collect each of ocarina_buttons). Vanilla always has them.
OCARINA_BUTTONS = ["Ocarina_A_Button", "Ocarina_C_up_Button", "Ocarina_C_down_Button", "Ocarina_C_left_Button",
                   "Ocarina_C_right_Button"]


def known_names(logic):
    """Every identifier an inventory entry can mean: words used by any rule or helper, every item the original
    game puts somewhere, and the aliases."""
    key = ("known", id(logic.graph))
    if key not in _CACHE:
        words = set(ALIASES) | NO_EFFECT
        texts = list(logic.helpers_text)
        for r in logic.graph:
            texts += [e["rule"] for e in r["exits"]] + list(r["locations"].values()) + list(r["events"].values())
            words |= {escape(k) for k in r["events"]}
        for t in texts:
            words |= set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", t))
        friendly = set()
        for loc in logic.locations.values():
            v = loc.get("vanilla_item")
            if v:
                v = v[4:] if v.startswith("Buy ") else v
                words.add(escape(v))
                friendly.add(v)
        friendly |= {k.replace("_", " ") for k in ALIASES}
        _CACHE[key] = (words, sorted(friendly))
    return _CACHE[key]


class Logic:
    def __init__(self, items, all_keys=False, tricks=(), glitches=False, hearts=3, data_dir=None):
        base = data_dir or HERE
        self.graph = _load("logic/world_graph.json", base)["regions"]
        self.regions = {r["region"]: r for r in self.graph}
        self.settings = _load("logic/vanilla_settings.json", base)
        key = ("helpers", base)
        if key not in _CACHE:
            helpers, params = {}, {}
            for k, v in _load("logic/helpers.json", base).items():
                m = re.match(r"(\w+)\((.*)\)$", k)
                body = ast.parse(v.strip(), mode="eval").body
                if m:
                    helpers[m.group(1)] = body
                    params[m.group(1)] = [p.strip() for p in m.group(2).split(",") if p.strip()]
                else:
                    helpers[k] = body
            raw = _load("logic/helpers.json", base)
            _CACHE[key] = (helpers, params, {i["name"]: i for i in _load("items.json", base)}, list(raw) + list(raw.values()))
        self.helpers, self.helper_params, self.locations, self.helpers_text = _CACHE[key]
        self.unknown_items = []  # (what you wrote, suggestions): ignored by the logic
        words, friendly = known_names(self)
        self.inv = {}
        for raw in items:
            raw = raw.strip()
            if not raw:
                continue
            n = 1
            m = re.match(r"(.*?)\s*[x\*:]\s*(\d+)$", raw)
            if m:
                raw, n = m.group(1), int(m.group(2))
            e = escape(raw)
            if e in ALIASES:
                ident, c = ALIASES[e]
                self.inv[ident] = max(self.inv.get(ident, 0), c * n if ident == "Bottle" else c)
            elif e in NEEDS_DUNGEON:
                self.unknown_items.append((raw, [f"{raw} (Forest Temple)", "--all-keys"]))
            elif e not in words:
                import difflib
                self.unknown_items.append((raw, difflib.get_close_matches(raw, friendly, n=3, cutoff=0.6)))
            else:
                self.inv[e] = self.inv.get(e, 0) + n
        self.fast = False  # True: rules only answer yes/no (no "what's missing"); used by bulk replays
        self.all_keys = all_keys
        self.tricks = set(tricks)
        self.all_tricks = "all" in self.tricks
        self.glitches = glitches
        self.hearts = hearts
        self.collected = set()  # events + auto-collected drops/shop items (escaped names)
        self.reached = set()    # (region, age)
        self._rule_cache = _CACHE.setdefault("rules", {})  # parsed rule ASTs are shared between instances

    # ------------------------------------------------------------ atoms
    def count(self, ident):
        n = self.inv.get(ident, 0) + (1 if ident in self.collected else 0) + FREE_KEYS.get(ident, 0)
        if ident in OCARINA_BUTTONS and not self.settings.get("shuffle_individual_ocarina_notes"):
            n += 1
        if self.all_keys and (ident.startswith("Small_Key_") or ident.startswith("Boss_Key_") or ident.startswith("Silver_Rupee_")):
            n = max(n, 99)
        return n

    def has_bottle(self):
        return any(("Bottle" in k or k == "Rutos_Letter") and v > 0 for k, v in self.inv.items())

    def trick_on(self, name):
        if name.startswith("logic_"):
            return self.all_tricks or name in self.tricks
        return self.glitches or name in self.tricks

    # ------------------------------------------------------------ evaluation
    def parse(self, rule):
        if rule not in self._rule_cache:
            self._rule_cache[rule] = ast.parse(rule.strip(), mode="eval").body
        return self._rule_cache[rule]

    def value(self, node, age, env):
        """Symbolic value for comparisons: settings -> their value, params -> bound symbol, names -> name."""
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            n = node.id
            if n in env:
                return env[n]
            if n == "age":
                return age
            if n in self.settings:
                return self.settings[n]
            return n
        return self.ev(node, age, env)[0]

    def ev(self, node, age, env):
        """Return (bool, missing:set[str]); missing is a small set of atoms that would satisfy a false rule."""
        T, F = (True, frozenset()), None
        if isinstance(node, ast.BoolOp):
            if self.fast:  # yes/no only: short-circuit, no explanation of what is missing
                want = isinstance(node.op, ast.Or)
                for v in node.values:
                    if self.ev(v, age, env)[0] == want:
                        return (want, frozenset())
                return (not want, frozenset())
            if isinstance(node.op, ast.And):
                miss, ok = set(), True
                for v in node.values:
                    b, m = self.ev(v, age, env)
                    if not b:
                        ok = False
                        miss |= m
                return (True, frozenset()) if ok else (False, frozenset(miss))
            best = None
            for v in node.values:
                b, m = self.ev(v, age, env)
                if b:
                    return T
                if best is None or self._rank(m) < self._rank(best):
                    best = m
            return False, best or frozenset()
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            b, _ = self.ev(node.operand, age, env)
            return (True, frozenset()) if not b else (False, frozenset() if self.fast else frozenset({"not " + ast.unparse(node.operand)}))
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return (node.value, frozenset() if node.value else frozenset({"False"}))
            if isinstance(node.value, str):  # quoted event
                e = escape(node.value)
                return (True, frozenset()) if self.count(e) else (False, frozenset({"event: " + node.value}))
            return (bool(node.value), frozenset())
        if isinstance(node, ast.Compare):
            left = self.value(node.left, age, env)
            ok = True
            for op, comp in zip(node.ops, node.comparators):
                right = self.value(comp, age, env)
                try:
                    r = {ast.Eq: left == right, ast.NotEq: left != right, ast.In: left in right if isinstance(right, (list, tuple, str)) else False,
                         ast.NotIn: left not in right if isinstance(right, (list, tuple, str)) else True,
                         ast.Lt: left < right, ast.LtE: left <= right, ast.Gt: left > right, ast.GtE: left >= right}[type(op)]
                except TypeError:
                    r = False
                ok = ok and r
                left = right
            if ok:
                return (True, frozenset())
            return (False, frozenset() if self.fast else frozenset({"condition: " + ast.unparse(node)}))
        if isinstance(node, ast.Tuple):  # (Item, count)
            name = self.value(node.elts[0], age, env)
            n = self.value(node.elts[1], age, env)
            n = n if isinstance(n, int) else self.settings.get(n, 1)
            if self.count(escape(name)) >= n:
                return True, frozenset()
            friendly = next((k for k, (ident, c) in ALIASES.items() if ident == escape(name) and c == n), None)
            return False, frozenset({f"{name} x{n}" + (f" ({friendly.replace('_', ' ')})" if friendly else "")})
        if isinstance(node, ast.Subscript):  # skipped_trials[Forest]
            return False, frozenset({"(trial not skipped in vanilla)"})
        if isinstance(node, ast.Name):
            return self.atom(node.id, age, env)
        if isinstance(node, ast.Call):
            return self.call(node, age, env)
        return False, frozenset({"? " + ast.unparse(node)})

    def atom(self, n, age, env):
        T = (True, frozenset())
        if n in env:
            sym = env[n]
            return self.atom(sym, age, {}) if isinstance(sym, str) else ((True, frozenset()) if sym else (False, frozenset({n})))
        if n == "is_child":
            return T if age == "child" else (False, frozenset({"be child"}))
        if n == "is_adult":
            return T if age == "adult" else (False, frozenset({"be adult"}))
        if n in ("at_day", "at_night", "at_dampe_time", "had_night_start"):
            return T  # basic: time of day can always be waited for
        if n == "has_bottle":
            return T if self.has_bottle() else (False, frozenset({"Bottle"}))
        if n in ("keysanity", "entrance_shuffle", "skip_child_zelda", "disable_trade_revert", "selected_adult_trade_item"):
            return False, frozenset({n})
        if n.startswith(("logic_", "glitch_", "adv_")):
            return T if self.trick_on(n) else (False, frozenset({"trick: " + n}))
        if n in self.helpers and not self.helper_params.get(n) and n not in self.inv:
            return self.ev(self.helpers[n], age, env)
        if n in self.settings:
            v = self.settings[n]
            return (True, frozenset()) if v else (False, frozenset({"setting: " + n}))
        return T if self.count(n) else (False, frozenset({n}))

    def call(self, node, age, env):
        fn = node.func.id if isinstance(node.func, ast.Name) else ast.unparse(node.func)
        args = node.args
        T = (True, frozenset())
        if fn == "here":
            # RuleParser.here(): an event in the rule's own region, which ANY age that reaches the region can set
            # (e.g. plant a bean as child, ride its platform as adult).
            region = getattr(self, "_here", None)
            ages = [a for a in ("child", "adult") if region and (region, a) in self.reached and self._age_live(a)]
            for a in ages:
                if self.ev(args[0], a, env)[0]:
                    return T
            return self.ev(args[0], ages[0] if ages else age, env)
        if fn == "at":
            region = self.value(args[0], age, env)
            ages = [a for a in ("child", "adult") if (region, a) in self.reached]
            for a in ages:
                b, m = self.ev(args[1], a, env)
                if b:
                    return T
            if not ages:
                return False, frozenset({f"region in logic: {region}"})
            return self.ev(args[1], ages[0], env)
        if fn in ("has_soul", "has_all_notes_for_song", "can_live_dmg"):
            return T
        if fn == "region_has_shortcuts":
            return False, frozenset({"dungeon shortcuts setting"})
        if fn in ("has_stones", "has_medallions", "has_dungeon_rewards", "has_hearts"):
            n = self.value(args[0], age, env)
            n = n if isinstance(n, int) else self.settings.get(n, 0)
            stones = ["Kokiri_Emerald", "Goron_Ruby", "Zora_Sapphire"]
            meds = ["Forest_Medallion", "Fire_Medallion", "Water_Medallion", "Shadow_Medallion", "Spirit_Medallion", "Light_Medallion"]
            pool = {"has_stones": stones, "has_medallions": meds, "has_dungeon_rewards": stones + meds}.get(fn)
            have = self.hearts + self.count("Heart_Container") + self.count("Piece_of_Heart") // 4 if fn == "has_hearts" else sum(1 for x in pool if self.count(x))
            return T if have >= n else (False, frozenset({f"{fn}({n})"}))
        if fn in self.helpers:
            params = self.helper_params.get(fn, [])
            new_env = {}
            for p, a in zip(params, args):
                if isinstance(a, ast.Name):
                    new_env[p] = env.get(a.id, a.id)
                else:
                    new_env[p] = self.value(a, age, env)
            return self.ev(self.helpers[fn], age, new_env)
        return False, frozenset({"? " + fn})

    def _rank(self, m):
        return (any(x.startswith(self.FIXED) for x in m), len(m))

    def rule(self, text, age, region=None):
        """Evaluate a rule as `age`. `region` is where the rule lives: here(...) needs it."""
        prev, self._here = getattr(self, "_here", None), region
        try:
            return self.ev(self.parse(text), age, {})
        finally:
            self._here = prev

    # ------------------------------------------------------------ search
    # Collected automatically once in logic: events, refills, shop purchases, and the Happy Mask Shop's masks (it lends
    # each mask again whenever asked, and each borrowed mask is what opens the next one in the chain).
    AUTO = {"Event", "Drop", "Shop", "MaskShop"}

    def solve(self):
        self.reached = {("Root", "child"), ("Root", "adult")}
        changed = True
        while changed:
            changed = False
            for region, age in list(self.reached):
                r = self.regions.get(region)
                if not r:
                    continue
                for ev_name, rl in r["events"].items():
                    e = escape(ev_name)
                    if e not in self.collected and self.rule(rl, age, region)[0]:
                        self.collected.add(e)
                        changed = True
                for ln, rl in r["locations"].items():
                    loc = self.locations.get(ln)
                    if loc and loc["type"] in self.AUTO and loc.get("vanilla_item"):
                        e = escape(loc["vanilla_item"])
                        if e not in self.collected and self.rule(rl, age, region)[0]:
                            self.collected.add(e)
                            changed = True
                for ex in r["exits"]:
                    st = (ex["to"], age)
                    if st not in self.reached and self.rule(ex["rule"], age, region)[0]:
                        self.reached.add(st)
                        changed = True
        # Root as adult is only meaningful once time travel is possible
        return self

    def region_ages(self, region):
        return [a for a in ("child", "adult") if (region, a) in self.reached and self._age_live(a)]

    def _age_live(self, age):
        return age == self.settings.get("starting_age", "child") or self.count("Time_Travel")

    FIXED = ("condition: ", "setting: ", "be adult", "be child", "not ", "False", "(trial", "dungeon shortcuts", "keysanity",
             "entrance_shuffle", "skip_child_zelda", "disable_trade_revert", "selected_adult_trade_item", "? ")

    HINT_SKIP = {"Farores Wind Warp"}  # randomizer modelling of FW warp points; misleading as a route hint

    def access_hint(self, region):
        """Cheapest route (fewest extra logic atoms) from the in-logic area into `region`."""
        import heapq
        if not hasattr(self, "_paths"):
            self._paths = None
        start = [(r, a) for (r, a) in self.reached if self._age_live(a)]
        dist = {s: frozenset() for s in start}
        prev = {}
        heap = [(0, i, s) for i, s in enumerate(start)]
        heapq.heapify(heap)
        tick = len(heap)
        goal = None
        while heap:
            c, _, st = heapq.heappop(heap)
            if st[0] == region:
                goal = st
                break
            if len(dist[st]) != c:
                continue
            r = self.regions.get(st[0])
            if not r or st[0] in self.HINT_SKIP:
                continue
            for ex in r["exits"]:
                for age in [st[1]]:
                    b, m = self.rule(ex["rule"], age, st[0])
                    if any(x.startswith(self.FIXED) for x in m):
                        continue  # needs a fixed setting or the other age: not something you can collect
                    m = frozenset(x for x in m if not x.startswith("region in logic: "))
                    nd = dist[st] | m
                    nxt = (ex["to"], age)
                    if nxt not in dist or len(nd) < len(dist[nxt]):
                        dist[nxt] = nd
                        prev[nxt] = st
                        tick += 1
                        heapq.heappush(heap, (len(nd), tick, nxt))
            if st[1] == "child" and not self._age_live("adult") and region != "Beyond Door of Time":
                # becoming adult needs time travel; offer it as one more atom
                nxt = (st[0], "adult")
                nd = dist[st] | {"Time_Travel"}
                if st[0] == "Root" and (nxt not in dist or len(nd) < len(dist[nxt])):
                    dist[nxt] = nd
                    prev[nxt] = st
                    tick += 1
                    heapq.heappush(heap, (len(nd), tick, nxt))
        if goal is None:
            return dict(note="no route found in the logic graph")
        route, cur = [], goal
        while cur in prev:
            route.append(cur[0])
            cur = prev[cur]
        route.append(cur[0])
        route = [x for i, x in enumerate(reversed(route)) if i == 0 or x != list(reversed(route))[i - 1]]
        return dict(route=route, as_age=goal[1], logic_wants=self.expand(dist[goal]))

    def expand(self, atoms):
        """Replace 'event: X' atoms by what the event's own rule wants (one level)."""
        out = set()
        for a in atoms:
            if a.startswith("event: "):
                ev = a[7:]
                src = next(((r, rl) for r in self.graph for k, rl in r["events"].items() if k == ev), None)
                if src:
                    r, rl = src
                    ages = self.region_ages(r["region"]) or ["child", "adult"]
                    wants = min((self.rule(rl, ag, r["region"])[1] for ag in ages), key=len)
                    out.add(f"{a} (in {r['region']}; needs {sorted(wants) or 'reaching that region'})")
                    continue
            out.add(a)
        return sorted(out)

    def location_status(self, name, explain=True):
        loc = self.locations[name]
        region = loc.get("region")
        rule = loc.get("logic_rule") or "True"
        ages_in = [a for a in self.region_ages(region) if self.rule(rule, a, region)[0]] if region else []
        out = dict(name=name, type=loc["type"], vanilla_item=loc.get("vanilla_item"), region=region,
                   scene=loc.get("scene_name") or loc.get("scene_enum"))
        if not loc.get("vanilla_item"):
            out["note_no_item"] = "the original game puts no item here, so list views skip it"
        if ages_in:
            out.update(status="in_logic", ages=ages_in)
            return out
        out["status"] = "not_in_standard_logic"
        out["note"] = NOTE
        if not explain:
            return out
        reg_ages = self.region_ages(region) if region else []
        if reg_ages:
            out["region_in_logic_as"] = reg_ages
            out["logic_wants_for_location"] = self.expand(min((self.rule(rule, a, region)[1] for a in reg_ages), key=len))
        else:
            out["logic_wants_to_enter_region"] = self.access_hint(region)
            out["logic_wants_for_location"] = self.expand(min((self.rule(rule, a, region)[1] for a in ("child", "adult")), key=len))
        return out


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    a = sys.argv[1:]

    def opt(name, default=None):
        if name in a:
            i = a.index(name)
            return a[i + 1] if i + 1 < len(a) else default
        return default
    items = [x for x in re.split(r"[,;]", opt("--items", ""))]
    tricks = [t.strip() for t in (opt("--tricks", "") or "").split(",") if t.strip()]
    L = Logic(items, all_keys="--all-keys" in a, tricks=tricks, glitches="--glitches" in a,
              hearts=int(opt("--hearts", 3))).solve()
    as_json = "--json" in a
    for raw, sugg in L.unknown_items:
        print(f"warning: unknown item {raw!r} was ignored." + (f" Did you mean: {', '.join(sugg)}?" if sugg else ""),
              file=sys.stderr)
    if L.unknown_items and "--strict" in a:
        sys.exit(2)
    if opt("--location"):
        q = opt("--location").lower()
        names = [n for n in L.locations if n.lower() == q] or [n for n in L.locations if q in n.lower()]
        res = [L.location_status(n) for n in names if L.locations[n].get("region")]
        if as_json:
            print(json.dumps(res, indent=1, ensure_ascii=False))
        else:
            for r in res:
                print(f"{r['name']}: {r['status']}" + (f" as {r['ages']}" if r.get("ages") else ""))
                if r["status"] != "in_logic":
                    if r.get("logic_wants_to_enter_region"):
                        print(f"  to enter {r['region']}, logic wants: {r['logic_wants_to_enter_region']}")
                    print(f"  logic wants for the location itself: {r['logic_wants_for_location']}")
            if res and any(r["status"] != "in_logic" for r in res):
                print(NOTE)
        return
    scene_q = (opt("--scene") or "").lower()
    rows = []
    for n, loc in L.locations.items():
        if not loc.get("region") or not loc.get("vanilla_item") or loc["type"] in ("Event", "Drop", "HintStone", "Hint"):
            continue
        if scene_q and scene_q not in (loc.get("scene_name") or "").lower() and scene_q not in (loc.get("region") or "").lower():
            continue
        rows.append(L.location_status(n, explain="--explain" in a))
    inl = [r for r in rows if r["status"] == "in_logic"]
    summary = dict(inventory=L.inv, unknown_items=[dict(name=r, did_you_mean=sg) for r, sg in L.unknown_items], adult_in_logic=bool(L.count("Time_Travel")), events_in_logic=sorted(L.collected),
                   locations_checked=len(rows), in_logic=len(inl), not_in_standard_logic=len(rows) - len(inl), note=NOTE)
    if as_json:
        print(json.dumps(dict(summary=summary, locations=rows), indent=1, ensure_ascii=False))
        return
    print(f"In logic: {len(inl)} of {len(rows)} locations. Adult in logic: {summary['adult_in_logic']}")
    for r in inl:
        print(f"  [{'/'.join(r['ages'])}] {r['name']}  ({r['vanilla_item']})")
    print(f"{len(rows) - len(inl)} more are not in standard logic yet (use --location NAME to see what logic wants).")
    print(NOTE)


if __name__ == "__main__":
    main()
