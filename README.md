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

You only need **Python 3** and your ROM: no git, no downloads, no compiler. It takes a few seconds.

```powershell
python tools/build.py --rom "C:\path	o\Zelda no Densetsu - Toki no Ocarina (Japan).z64"
```

(On Mac or Linux it's the same command, using `python3`.) The script checks that the ROM is NTSC-J 1.0
(`.z64`, MD5 `9f04c8e68534b870f707c247fa4b50fc`), then writes everything into `ootmap/`. Add `--out <folder>` to
build somewhere else; the evaluator and docs are copied there too.

Windows shortcut: `.uild.ps1 -Rom "<path>"` does the same. If PowerShell says running scripts is disabled,
use the `python` command above instead.

## Use

- [ootmap/HOW_TO_USE.md](ootmap/HOW_TO_USE.md): the logic evaluator (`logic_eval.py`), in plain steps.
- [ootmap/BOT_GUIDE.md](ootmap/BOT_GUIDE.md): every data file and field, written for bot authors.
- [ootmap/ACTIONS.md](ootmap/ACTIONS.md): every action Link can be in, and the physics of every move
  (sidehops, backflips, backwalking, rolls, jumps, slopes), read from the game code.
- `python ootmap/query.py`: quick lookups (`find`, `scene`, `route`, `entrance`, `region`, `func`, `warps`).

## How it works

- `data/meta/`: the **metadata pack**, shipped with the repo. It holds the names, enums and param layouts from
  [zeldaret/oot](https://github.com/zeldaret/oot), the [OoT Randomizer](https://github.com/OoTRandomizer/OoT-Randomizer)
  logic set to vanilla settings, and the decomp function index. It contains nothing read from the ROM, and
  it's why a build needs only your ROM.
- `tools/ootrom.py`, `tools/extract_map.py`, `tools/decode.py`: read the ROM directly (file table, Yaz0, scene
  and room headers, actors, exits, collision) and decode actor parameters.
- `tools/build_bot_db.py`: joins the ROM data with the logic into items, graphs and warps.
- `tools/build.py`: runs all of the above.

### Maintainers: regenerating the metadata pack

Only needed after changing the pinned decomp or randomizer versions (in `tools/fetch_refs.py`):

```powershell
python -I tools/fetch_refs.py
```
```powershell
python -I tools/make_metadata.py
```

This fetches both projects into `ref/` (git-ignored) and rewrites `data/meta/`. Neither project's code is
run; their files are only read as text and data.

## Publishing

By default `.gitignore` keeps out:
- your ROM and the `ref/` folder;
- the generated `ootmap/` data, because it's derived from Nintendo's game data.

The tools, docs, query tool, evaluator and the metadata pack are published. If you decide to publish the generated data
too, delete the last block of `.gitignore`. That's your call to make.

## Credits

- [zeldaret/oot](https://github.com/zeldaret/oot): names, enums and data formats.
- [OoT Randomizer](https://github.com/OoTRandomizer/OoT-Randomizer): logic rules (MIT; see `THIRD_PARTY_NOTICES.md`).

The Legend of Zelda is a trademark of Nintendo. This project isn't affiliated with Nintendo.
