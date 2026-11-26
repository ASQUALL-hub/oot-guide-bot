"""Index every C function in the decomp and every place the code sends Link to an entrance.

Reads source as text only. usage: python -I scan_source.py <tools_dir> <decomp_root> <out_dir>
"""
import sys
import os
import re
import json

sys.path.insert(0, sys.argv[1])
from headers import Decomp  # noqa: E402

ROOT, OUT = sys.argv[2], sys.argv[3]
D = Decomp(ROOT)
ENTR = D.entrance_by_enum()
SCENE_ENUMS = {v["enum"] for v in D.scenes.values()}

FUNC_RE = re.compile(r"^(?!typedef|static\s+\w+\s+\w+\s*\[|#)([A-Za-z_][\w\s\*\(\),]*?)\b([A-Za-z_]\w*)\s*\(([^;{}]*)\)\s*\{", re.M)
KEYWORDS = {"if", "for", "while", "switch", "return", "sizeof", "else", "do", "case"}
DEST_RE = re.compile(r"(nextEntranceIndex|entranceIndex|nextCutsceneIndex|respawn\[[A-Z_]+\]\.entranceIndex)\s*=\s*([^;]+);")
COND_RE = re.compile(r"^\s*(?:\}\s*)?(if\s*\(|else if\s*\(|else\b|case\s+[^:]+:|switch\s*\(|default:)")


def strip_comments_keep_lines(s):
    def rep(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    s = re.sub(r"/\*.*?\*/", rep, s, flags=re.S)
    s = re.sub(r"//[^\n]*", rep, s)
    return s


def match_brace(s, i):
    depth = 0
    in_str = None
    while i < len(s):
        c = s[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == in_str:
                in_str = None
        elif c in "\"'":
            in_str = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return len(s) - 1


def owner_of(rel):
    parts = rel.replace("\\", "/").split("/")
    if len(parts) > 3 and parts[1] == "overlays":
        kind = parts[2]
        name = parts[3][4:] if parts[3].startswith("ovl_") else parts[3]
        return kind, name
    return parts[1] if len(parts) > 2 else "src", None


def resolve_entr(expr):
    expr = expr.strip()
    toks = re.findall(r"ENTR_\w+", expr)
    res = []
    for t in toks:
        i = ENTR.get(t)
        if i is not None:
            e = D.entrances[i]
            res.append(dict(entrance_enum=t, entrance=i, entrance_hex=f"{i:#05x}", scene_enum=e["scene"], spawn=e["spawn"]))
        else:
            res.append(dict(entrance_enum=t))
    return res


def main():
    os.makedirs(OUT, exist_ok=True)
    functions, dests = [], []
    src = os.path.join(ROOT, "src")
    all_names = set()
    files = []
    for dp, dn, fn in os.walk(src):
        for f in fn:
            if f.endswith(".c"):
                files.append(os.path.join(dp, f))
    files.sort()
    parsed = []
    for path in files:
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        with open(path, encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
        s = strip_comments_keep_lines(raw)
        raw_lines = raw.splitlines()
        for m in FUNC_RE.finditer(s):
            ret, name, args = m.group(1).strip(), m.group(2), m.group(3)
            if name in KEYWORDS or ret.split()[-1:] in (["return"], ["else"]) or "=" in ret:
                continue
            start = m.end() - 1
            end = match_brace(s, start)
            l0 = s.count("\n", 0, m.start()) + 1
            l1 = s.count("\n", 0, end) + 1
            parsed.append((rel, name, ret, args, l0, l1, s[start:end + 1], raw_lines))
            all_names.add(name)
    for rel, name, ret, args, l0, l1, body, raw_lines in parsed:
        kind, owner = owner_of(rel)
        calls = sorted({c for c in re.findall(r"\b([A-Za-z_]\w*)\s*\(", body) if c in all_names and c != name})
        ret_clean = re.sub(r"\s+", " ", ret)
        args_clean = re.sub(r"\s+", " ", args).strip()
        fn = dict(name=name, file=rel, line=l0, end_line=l1, signature=f"{ret_clean} {name}({args_clean})",
                  module=kind, owner=owner, calls=calls,
                  static=ret_clean.startswith("static"))
        # leading doc comment in the original source
        doc = []
        k = l0 - 2
        while k >= 0 and (raw_lines[k].strip().startswith(("*", "/*", "//")) or raw_lines[k].strip().endswith("*/")):
            doc.insert(0, raw_lines[k].strip())
            k -= 1
        if doc:
            fn["doc"] = " ".join(x.lstrip("/* ").rstrip("*/ ") for x in doc).strip()
        touches = sorted(set(re.findall(r"\b(ENTR_\w+)", body)))
        if touches:
            fn["entrances_referenced"] = touches
        functions.append(fn)
        # destination writes with condition context
        blines = body.splitlines()
        for j, line in enumerate(blines):
            for dm in DEST_RE.finditer(line):
                ctxl = []
                for q in range(j - 1, max(-1, j - 12), -1):
                    if COND_RE.match(blines[q]):
                        ctxl.insert(0, raw_lines[l0 - 1 + q].strip() if l0 - 1 + q < len(raw_lines) else blines[q].strip())
                        if len(ctxl) >= 4:
                            break
                expr = dm.group(2)
                dests.append(dict(file=rel, line=l0 + j, function=name, module=kind, owner=owner,
                                  field=dm.group(1), expression=expr.strip(), targets=resolve_entr(expr),
                                  conditions_nearby=ctxl,
                                  statement=raw_lines[l0 - 1 + j].strip() if l0 - 1 + j < len(raw_lines) else line.strip()))
    with open(os.path.join(OUT, "functions.json"), "w") as f:
        json.dump(functions, f, indent=0)
    with open(os.path.join(OUT, "code_entrance_writes.json"), "w") as f:
        json.dump(dests, f, indent=1)
    print("functions:", len(functions), "entrance writes:", len(dests),
          "with resolved targets:", sum(1 for d in dests if any("entrance" in t for t in d["targets"])))


if __name__ == "__main__":
    main()
