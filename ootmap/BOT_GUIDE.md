# Ocarina of Time (NTSC-J 1.0) map database for bots

Everything here was extracted from the ROM `Zelda no Densetsu - Toki no Ocarina (Japan).z64`
(MD5 `9f04c8e68534b870f707c247fa4b50fc`, the decomp's `ntsc-1.0` JP build). Names come from the
zeldaret/oot decompilation. How items are obtained comes from the OoT Randomizer's logic files, run
with vanilla settings. All files are plain UTF-8 JSON.

## Start here

| Question a bot has | File | Key fields |
|---|---|---|
| Where is item X and how do I get it? | `items.json` | `name`, `vanilla_item`, `scene_enum`, `rom_actors[].room/pos/layers`, `how_obtained`, `logic_rule` |
| What leads where? (logic-free, straight from the ROM) | `scene_graph.json` | `edges[]` (loading zones, grotto holes): `at` = where to walk, `arrive_at` = where you land |
| What leads where, and what do I need? | `logic/world_graph.json` | `regions[].exits[]`: `rule`, `entrance`, `loading_zones`, `arrive_at`; `regions[].locations` |
| What does a rule word mean? | `logic/helpers.json`, `logic/vanilla_settings.json` | see "Reading logic rules" |
| Warp songs, blue warps, owls, grottos, cutscene exits | `warps.json` | |
| Everything inside one scene | `scenes/<id>_<ENUM>.json` | layers → spawns, exits, doors; rooms → layers → actors (decoded) |
| What does item X do, how do I use it, at which age? | `game.json` `items[]`, `songs[]` (readable: `GAME_GUIDE.md`) | `use`, `usable_by`, `does`, `slot`/`menu_row`/`menu_col`, `capacity_by_upgrade_level`, `magic_cost`, `found_at` |
| What does item/event X unlock? What does location Y need? | `game.json` | `strictly_needed_for[X]` (`directly_unlocks`, `locations`), `location_needs[Y]` (`directly`, `all`) |
| In what order is the game played? | `game.json` | `main_quest[]`, `playthrough.spheres[]` |
| What hurts enemy X? What can hit object Y? | `game.json` `actors` | `health`, `damage_tables[]`, `can_be_hit_by`, `attacks` |
| How do I equip things? | `game.json` `menus` | item grid, equipment grid, buttons |
| What can Link do, and how does each move behave? (speed, height, airtime, distance) | `actions.json` (readable version: `ACTIONS.md`) | `ground_moves`, `jumps[].flat_ground/chained`, `rules`, `speedrun_tech`, `player_actions` (all 89 action states), `body`, `attack_hitboxes`, `world_collision` (clip conditions), `frame_order` |
| Walkable geometry, walls, water, void planes | `collision/<id>_<ENUM>.json` | `vertices`, `polygons[].v/surface`, `surfaces[]`, `waterboxes` |
| What entrance N is | `entrances.json` | `scene_enum`, `spawn`, `layer`, `base_entrance` |
| Every function in the game's code | `code/functions.json` | `name`, `file`, `line`, `signature`, `calls`, `owner` (actor) |
| Every place code sends Link somewhere | `code/code_entrance_writes.json` | `function`, `conditions_nearby`, `targets` |
| What actor/item/object id N is | `tables/*.json` | actors (with description + param layout), get_items, items, objects, collectible_drops |

`python logic_eval.py --items "..."` tells a bot which locations are **in standard logic** with its
current items (see "Logic evaluator" below).

`python query.py ...` answers the common questions directly (`find`, `scene`, `route`, `entrance`,
`region`, `func`, `warps`, `item`, `unlocks`, `needs`, `quest`; add `--json` for machine output). It needs only Python 3.

## Coordinates and layers

- Positions are game units `[x, y, z]`, with **y up**.
- Rotations are binary angles (0x10000 = 360°); `rot_y_deg` gives the yaw in degrees.
- Every scene has **layers** (the game calls them scene setups): `child_day`, `child_night`, `adult_day`,
  `adult_night`, then `cutscene_N`. Each layer has its own actors, exits and spawns.
  `header_source` tells you whether the layer has its own data (`own`) or reuses another one
  (`fallback_base`, `fallback_adult_day`). That fallback is how the game itself resolves a missing layer.
- A scene has rooms. Doors and transition planes (`transition_actors`, shown as `room_links` in
  `scene_graph.json`) connect `front_room` and `back_room`.

## Entrances, exits and loading zones

- An **entrance** index (0x000–0x613) means "scene S, spawn point P". Entrances come in groups of
  4: base + 0..3 for child day, child night, adult day and adult night. Entrances past those are cutscene versions.
  `entrances.json` gives each entrance's `base_entrance` and `layer`.
- A **spawn** points at a player-start position (`player_entries`) and a room.
- An **exit** is a slot in a scene's exit list, and its value is an entrance. Collision polygons whose surface
  has `exit_index = k` form loading zone k. `loading_zone.center/bbox` is where to walk. Exits with
  `loading_zone: null` are used by actors or cutscenes, not by walking.
- Grotto holes (`Door_Ana`) are exits too. Check `requires` before using one: hidden grottos need a bomb or
  hammer, or Song of Storms played within 200 units. Generic grotto chests get their contents from the hole's params.
- Warps the ROM data doesn't contain (blue warps, warp songs, owl flights, scripted exits) are in
  `warps.json` and `code/code_entrance_writes.json`. Each one comes with the `if`/`case` lines that guard it,
  for example "adult → `ENTR_SACRED_FOREST_MEADOW_3`, else `_2`".
- Void-outs: a floor whose surface `floor_property` is 5 respawns Link at the last entrance.

## Moving between floors (for path planners)

Collision floors are **not a welded mesh**. Neighbouring triangles often duplicate vertices or meet at
T-junctions, so joining floors only where they share an exact edge leaves false islands. Merge vertices by
position, or join edges that overlap. Then add these links, taken from the player code
(`z_player.c` `sAgeProperties` and the ledge checks):

| Move | Adult | Child | Conditions |
|---|---|---|---|
| Ledge climb-up | top 18–111 units above feet | top 18–71 units above feet | top floor is fairly flat (normal.y > ~0.855); the wall is **not** type 1, 2 or 3 |
| Climb type by height | <41 hop, 41–59, 59–79.4, ≥79.4 hang-and-pull | <27, 27–39, 39–47, ≥47 | same as above |
| Catch a ledge while falling/jumping | ledge up to ~150 above Link, after falling >70 | same rule (scaled) | moving toward the wall |
| Ladder (wall type 2), climbable surface (type 4) | any height | any height | a face-the-wall climb starts when the top is ≥79 above |
| Ladder top (type 3) | climb down from above | climb down from above | marks where a ladder can be grabbed from the top |
| Crawlspace (types 5/6) | no | yes | child only |
| Drop | any height | any height | fall damage only; avoid landing on void floors (`floor_property` 5) |

Wall types 1–3 block ledge grabs. Moving platforms, bridges, doors and pushable blocks are actors with their
own collision, so they aren't in `collision/*.json`. Check `scenes/*.json` actors for those.

## How the game fits together (`game.json`)

Built by `tools/build_game.py` from the logic, the ROM and the game's own tables. Text with `curated: true` is
hand-written; every number comes from the game code (`sources` names the file).

- **`items[]`**: every inventory item, equipment piece, upgrade and quest item: how to use it (`use`), the age that
  can use it (`usable_by`, from `gItemAgeReqs`), its pause-menu `slot` with `menu_row`/`menu_col`, ammo
  `capacity_by_upgrade_level`, `magic_cost`, sword `damage_flags`, hookshot `reach_units`, where the original game
  puts it (`found_at`, with the sphere), and `strictly_needed_for`.
- **`songs[]`**: notes (from `gOcarinaSongButtons`), effect, where each is learned. `ocarina_spots[]` lists every
  En_Okarina_Tag in the ROM (scene, room, position, which song, what it does, switch flag); `song_of_time_blocks[]`
  lists every Song of Time block.
- **`playthrough`**: the original item layout replayed through standard logic. Sphere 0 is everything in logic at
  the start; each later sphere is what the previous one opens. Where standard logic can't model the original route,
  a step says so (`trick_needed`, `key_rule_relaxed`) instead of silently stopping.
- **`strictly_needed_for[X]`**: the game replayed from the start without X (an item, or `event: ...`).
  `locations` counts what stays out of standard logic; `directly_unlocks` lists the checks where X is an immediate
  requirement; `location_names` lists everything.
- **`location_needs[Y]`**: the reverse: `all` key items and events Y strictly needs, and `directly` (minus anything
  another item on the list already needs).
- **`main_quest[]`**: the story in order, each step with its checks, sphere and needs.
- **`events[]`**: every logic event, where it's set, its rule and what needs it.
- **`trade_quests`**, **`menus`** (how to pause, switch pages, assign C buttons and equip; the Kokiri Sword is not put
  on B automatically).
- **`combat`**: the 32 damage types, what each sword uses for a swing and a jump attack, and the usual damage per
  attack type. **`actors`**: per actor, `health`, `damage_tables` (damage and reaction per attack type),
  `can_be_hit_by` (what its colliders accept), `attacks` (damage it deals to Link: 16 = one heart), and where it's
  placed in the ROM.

"Strictly needed" uses standard logic, so it never means unreachable: a trick or glitch may get there anyway.

## Items: how they're tracked

Each `items.json` record has `type`:
- `Chest`: `En_Box`. Opening it sets the chest's treasure flag for that scene.
- `Collectable`: freestanding Pieces of Heart, keys and similar. Picking one up sets a collectible flag.
- `GS Token`: Gold Skulltulas. `gs_flags.byte/mask` is the save-file bit. Some skulltulas spawn from trees,
  soft-soil patches or crates; `rom_actors` points at that spawner and `decoded.spawned_by` says how to reveal it.
- `Pot`, `Crate`, `SmallCrate`, `Beehive`, `Freestanding`, `Wonderitem`, `SilverRupee`, `RupeeTower`: the exact
  actor, given as `xflag.room/layer/actor_number`. `actor_number` counts from 1.
- `Scrub`/`GrottoScrub`: Business Scrubs (`En_Shopnuts`/`En_Dns`). `Shop`: shopkeeper inventory (`En_Ossan`).
- `NPC`, `Song`, `Cutscene`, `Boss`, `BossHeart`, `MaskShop`, `HintStone`, `Event`: rewards from characters or events.
  Use `region` and `logic_rule`.
- `rom_note` explains any item that some other actor spawns at runtime.

There are 1,448 vanilla-game locations. All 1,238 physical ones are linked to a ROM actor (or to the actor that
spawns them). The other 210 are NPC rewards, songs, hints and events.

## Reading logic rules

Rules are boolean expressions in the randomizer's syntax:
- `Item_Name` means you have it (e.g. `Kokiri_Sword`, `Progressive_Hookshot`). `(Item, n)` means you have at least n.
- `is_child` / `is_adult`, `at_day` / `at_night`.
- A word defined in `logic/helpers.json` is a macro, for example `can_use(Bow)` or `can_play(Song_of_Storms)`.
- A word in `logic/vanilla_settings.json` is a setting fixed to its vanilla value. Any word starting with
  `logic_` is an optional trick. Standard logic treats tricks as false, but a speedrun bot may know them.
- A quoted name like `'Defeat King Dodongo'` is an event. Events are set by `regions[].events`.
- `here(...)` and `at('Region', ...)` evaluate a rule as if you were in that region.

Reachability: start at the region `Root`, then repeatedly follow every exit whose rule holds, collecting
the locations and events whose rules hold, until nothing changes.

## Logic evaluator (`logic_eval.py`)

This is a basic evaluator. It never says a place is unreachable, because this data is also meant for
speedrunning. Each location gets one of two statuses:
- `in_logic`: obtainable with the given items under glitchless, no-trick rules (`ages` says child, adult or both).
- `not_in_standard_logic`: what the rules would want (`logic_wants_*`, including a suggested `route` of
  regions). The location may still be reachable with tricks, glitches or skips. Trick names show up as
  alternatives, e.g. `trick: logic_water_bk_jump_dive`.

```
python logic_eval.py --items "Kokiri Sword, Deku Shield, Slingshot, Bomb Bag"
python logic_eval.py --items "..." --location "Deku Tree Slingshot Chest"
python logic_eval.py --items "..." --scene "Forest Temple" --explain --json
```
Options:
- `--all-keys`: assume every small key, boss key and silver rupee.
- `--tricks all` or `--tricks logic_x,logic_y`: turn tricks on.
- `--glitches`: also turn on the `glitch_*`/`adv_*` toggles.
- `--hearts N`: starting heart count.

Item names can be written normally (`Saria's Song`, `Small Key (Forest Temple) x3`, `Longshot`,
`Golden Gauntlets`, `Ocarina of Time`). Progressive items are counted for you.

The evaluator collects events, refills (sticks, nuts, bugs, fish, fairies) and shop purchases on its own once
they're in logic. It does not collect chest or NPC items for you: the bot reports what it actually has. Adult
access opens once the Master Sword pedestal is in logic. Simplifications: time of day is always treated as
available, rupees and wallet size are ignored, and `at()`/`here()` are approximated. From Python you can also
use `Logic(items).solve().location_status(name)`. Like the randomizer with keys in their original places, it counts one
free Fire Temple small key.

## Limits

- Names, enums and param layouts come from the decomp source. The data itself (actors, exits, spawns,
  collision, entrance/scene/actor tables) was read from this ROM. The 37 entrance-table entries for debug test
  scenes don't exist in retail.
- Function ROM/RAM addresses aren't included: matching a function to an address requires building the decomp
  (an IDO toolchain on Linux). Actor overlay VRAM addresses are in `tables/actors.json`.
- Not exported: model and texture meshes, cutscene scripts (only whether a layer has one, and the exits
  cutscenes trigger), audio, and dialogue text.
- The decomp leaves most floor and wall type numbers unnamed. Only the ones confirmed in code are labeled
  (`floor_note` / `wall_note`). Hookshot targets, exits, water boxes and void floors are exact.
- `logic_rule` follows the randomizer's model of the game: glitchless play, tricks only where named. It describes
  what is guaranteed, not what is possible, so a speedrun route can legitimately ignore it.
- This database covers the original game only, not Master Quest.

## Rebuilding

Run `python tools/build.py --rom <path to your ROM>` from the repo root. It needs only Python 3 and the ROM:
names, enums, logic and the function index come from the bundled metadata pack in `data/meta/`.
`tools/extract_map.py` reads the ROM (scenes, collision, entrances, tables), `tools/build_bot_db.py` joins it with
the logic (items, graphs, warps), `tools/build_actions.py` adds Link's moves, and `tools/build_game.py` adds `game.json`. Maintainers regenerate `data/meta/` with `tools/fetch_refs.py` +
`tools/make_metadata.py`.
