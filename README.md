# OoT Guide Bot: a bot-readable map of Ocarina of Time

Turns your own copy of *The Legend of Zelda: Ocarina of Time* (NTSC-J 1.0) into JSON that any bot can read:
- **Items:** every item location and how to get it.
- **Exits and warps:** every loading zone, grotto, warp song, blue warp and owl flight, with positions.
- **Geometry:** walkable collision for every scene.
- **Logic:** the requirement graph.
- **Functions:** an index of every function in the decompiled game code.

It also includes a basic logic evaluator. It reports what's in logic with your items, and it never says
anything is unreachable, so it's safe to use for speedrun routing.

**No ROM or Nintendo data is included.** You build the database locally from a ROM you own.

## Build

You need git and Python 3. Then run this in PowerShell from this folder:

```powershell
.\build.ps1 -Rom "C:\path\to\Zelda no Densetsu - Toki no Ocarina (Japan).z64"
```

The script checks that the ROM is the right version and fetches the two reference projects (pinned versions).
Then it writes everything into `ootmap\`.

## Use

- [ootmap/HOW_TO_USE.md](ootmap/HOW_TO_USE.md): the logic evaluator (`logic_eval.py`), in plain steps.
- [ootmap/BOT_GUIDE.md](ootmap/BOT_GUIDE.md): every data file and field, written for bot authors.
- `python ootmap/query.py`: quick lookups (`find`, `scene`, `route`, `entrance`, `region`, `func`, `warps`).

## How it works

- `tools/ootrom.py`, `tools/extract_map.py`, `tools/decode.py`: read the ROM directly (file table, Yaz0, scene
  and room headers, actors, exits, collision) and decode actor parameters.
- `tools/scan_source.py`: indexes functions and entrance changes in the [zeldaret/oot](https://github.com/zeldaret/oot)
  decompilation. The decomp is used for names and formats only; none of its code is run.
- `tools/build_bot_db.py`: joins the ROM data with the [OoT Randomizer](https://github.com/OoTRandomizer/OoT-Randomizer)
  logic, set to vanilla settings. The logic files are read as data and never executed.

## Publishing

By default `.gitignore` keeps out three things:
- your ROM and the `ref/` folder (which also contains a copy of the ROM);
- the generated `ootmap/` data, because it's derived from Nintendo's game data;
- the function index built from the decomp.

Only the tools, docs, query tool and evaluator are published. If you decide to publish the generated data
too, delete the last block of `.gitignore`. That's your call to make.

## Credits

- [zeldaret/oot](https://github.com/zeldaret/oot): names, enums and data formats.
- [OoT Randomizer](https://github.com/OoTRandomizer/OoT-Randomizer): logic rules (MIT; see `THIRD_PARTY_NOTICES.md`).

The Legend of Zelda is a trademark of Nintendo. This project isn't affiliated with Nintendo.
