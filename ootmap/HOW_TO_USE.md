# How to use the logic evaluator

`logic_eval.py` tells you (or your bot) which item locations in Ocarina of Time are **in logic**
with the items you have right now. It only needs Python 3. Run it from inside the `ootmap` folder.

## 1. Basic check: what can I get right now?

```powershell
python logic_eval.py --items "Kokiri Sword, Deku Shield"
```

You get a count, then a list of every location that's in logic, tagged with the age it works for:

```
In logic: 66 of 1369 locations. Adult in logic: False
  [child] KF Midos Top Left Chest  (Rupees (5))
  ...
```

## 2. One location: why isn't it in logic?

```powershell
python logic_eval.py --items "Kokiri Sword, Deku Shield" --location "Queen Gohma"
```

```
Queen Gohma: not_in_standard_logic
  to enter Queen Gohma Boss Room, logic wants: {'route': [...], 'as_age': 'child', 'logic_wants': ['Slingshot']}
```

- `route` is the chain of areas the logic would take you through.
- `logic_wants` is what the logic expects you to have along the way.

**"Not in standard logic" never means unreachable.** It only means the glitchless, no-trick rules don't
guarantee it. A speedrun route using tricks, glitches or skips may get there anyway.

## 3. One area only

```powershell
python logic_eval.py --items "Kokiri Sword, Deku Shield, Slingshot" --scene "Deku Tree"
```

## Writing item names

- Use normal names, separated by commas: `Saria's Song, Bomb Bag, Hover Boots`.
- For more than one of something, add `x3`: `Small Key (Forest Temple) x3`.
- Upgrades can go by name: `Hookshot` / `Longshot`, `Goron Bracelet` / `Silver Gauntlets` / `Golden Gauntlets`,
  `Silver Scale` / `Golden Scale`, `Fairy Ocarina` / `Ocarina of Time`, `Magic`.
- Stones and medallions: `Kokiri Emerald, Goron Ruby, Zora Sapphire, Forest Medallion` ...

To become adult in logic, you need `Ocarina of Time, Song of Time` plus all three stones.

## Options

| Option | What it does |
|---|---|
| `--location "name"` | Explain one location (partial names work) |
| `--scene "name"` | Only list one area or dungeon |
| `--all-keys` | Pretend you have every small key, boss key and silver rupee |
| `--tricks all` | Allow every known trick (or list some: `--tricks logic_dc_jump,logic_lens_botw`) |
| `--glitches` | Also allow the glitch toggles |
| `--hearts 5` | Your heart count (default 3) |
| `--explain` | Add the "what logic wants" detail to list and area views (slower) |
| `--json` | Machine-readable output for bots |

## Using it from a bot

From the command line, add `--json` and read the result:

```powershell
python logic_eval.py --items "Kokiri Sword, Deku Shield" --json
```

From Python (run inside the `ootmap` folder):

```python
from logic_eval import Logic

logic = Logic(["Kokiri Sword", "Deku Shield", "Slingshot"]).solve()
print(logic.location_status("Queen Gohma"))
```

Each result has a `status` of `in_logic` (with `ages`) or `not_in_standard_logic` (with `logic_wants_*`).

## What does an item do, and what does it unlock?

`query.py` answers these from `game.json` (built with the rest of the map):

```powershell
python query.py item "hookshot"
```
```powershell
python query.py unlocks "bomb bag"
```
```powershell
python query.py needs "water temple longshot chest"
```
```powershell
python query.py quest
```

- `item`: how to use it, which age, ammo or magic cost, where it is in the original game, and how much of the game is
  out of standard logic without it.
- `unlocks`: what an item or event opens directly, and how many locations sit behind it in total.
- `needs`: the key items and events a location strictly needs (directly, and everything in all).
- `quest`: the main story in order. `GAME_GUIDE.md` has all of this as a readable page.

## Good to know

- Tell it everything you've collected. It doesn't add chest or NPC items by itself.
- It does handle the small stuff automatically: refills (sticks, nuts, bugs, fish, fairies), shop purchases
  and story events.
- It's basic: night and day are always treated as available, and rupees and wallet size are ignored.
- Like the randomizer with keys in their original places, it counts one free Fire Temple small key.
- To find where an item physically is (room and position), use `python query.py find "item name"`.
  `BOT_GUIDE.md` explains all the data files.
