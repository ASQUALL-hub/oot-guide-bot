"""OoT Randomizer logic data: read from a randomizer checkout (as data: ast/json, never executed),
or from the bundled metadata pack (data/meta/ootr.json)."""
import ast
import glob
import json
import os
import re


def read_logic_file(path):
    s = ""
    with open(path, encoding="utf-8") as f:
        for line in f:
            s += line.split("#")[0].replace("\n", " ")
    return json.loads(re.sub(" +", " ", s))


def py_literal_assign(path, var):
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in tree.body:
        targets, val = [], None
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            val = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
            val = node.value
        if var in targets:
            if isinstance(val, ast.Call) and val.args:  # OrderedDict([...])
                val = val.args[0]

            class NoCalls(ast.NodeTransformer):  # e.g. shop_address(0, 0) -> None (ROM addresses we don't need)
                def visit_Call(self, node):
                    return ast.copy_location(ast.Constant(None), node)
            val = ast.fix_missing_locations(NoCalls().visit(val))
            return ast.literal_eval(val)
    raise KeyError(var)


def gossip_stones(root):
    """Hints.py gossipLocations: {text id: GossipStone(hint area, location name)} -> {text id: location name}.
    In the ROM a gossip stone (En_Gs) shows text 0x400 + (params & 0xFF), so the text id identifies the actor."""
    with open(os.path.join(root, "Hints.py"), encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in tree.body:
        target = node.target if isinstance(node, ast.AnnAssign) else (node.targets[0] if isinstance(node, ast.Assign) else None)
        if getattr(target, "id", None) == "gossipLocations":
            return {k.value: v.args[1].value for k, v in zip(node.value.keys, node.value.values)}
    raise KeyError("gossipLocations")


def load_source(root):
    regions = []
    for p in sorted(glob.glob(os.path.join(root, "data", "World", "*.json"))):
        if p.endswith(" MQ.json"):
            continue  # this ROM is the original (non-Master-Quest) game
        for r in read_logic_file(p):
            r["_file"] = os.path.basename(p)
            regions.append(r)
    return dict(
        scene_names={k: v[2] for k, v in py_literal_assign(os.path.join(root, "SceneList.py"), "SCENE_TABLE").items()},
        locations=dict(py_literal_assign(os.path.join(root, "LocationList.py"), "location_table")),
        regions=regions,
        helpers=read_logic_file(os.path.join(root, "data", "LogicHelpers.json")),
        shuffle_table=py_literal_assign(os.path.join(root, "EntranceShuffle.py"), "entrance_shuffle_table"),
        gossip_stones=gossip_stones(root),
    )


def _default_back(d):
    # JSON turns tuples into lists; the location code tells (room, setup, flag) tuples
    # apart from lists of such tuples, so restore that shape.
    if isinstance(d, list):
        if d and all(isinstance(x, list) for x in d):
            return [tuple(x) for x in d]
        return tuple(d)
    return d


def load_meta(path):
    if os.path.isdir(path):
        path = os.path.join(path, "ootr.json")
    with open(path, encoding="utf-8") as f:
        m = json.load(f)
    locs = {}
    for name, (typ, scene, default, addrs, vanilla, tags) in m["locations"].items():
        locs[name] = (typ, scene, _default_back(default), addrs, vanilla, tuple(tags) if tags else tags)
    return dict(scene_names={int(k): v for k, v in m["scene_names"].items()}, locations=locs, regions=m["regions"],
                helpers=m["helpers"], shuffle_table=m["shuffle_table"],
                gossip_stones={int(k): v for k, v in m.get("gossip_stones", {}).items()})


def load(path):
    if (os.path.isdir(path) and os.path.exists(os.path.join(path, "ootr.json"))) or path.endswith(".json"):
        return load_meta(path)
    return load_source(path)
