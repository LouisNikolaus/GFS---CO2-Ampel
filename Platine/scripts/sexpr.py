"""Minimaler S-Expression-Parser/-Writer fuer KiCad-Dateien."""
import copy
import os

KICAD = r"C:\Program Files\KiCad\10.0"
SYMDIR = os.path.join(KICAD, "share", "kicad", "symbols")


class Q(str):
    """Ein String, der beim Schreiben in Anfuehrungszeichen gesetzt wird."""


def parse(text):
    pos, n = 0, len(text)
    stack, cur = [], []
    while pos < n:
        c = text[pos]
        if c in " \t\r\n":
            pos += 1
        elif c == "(":
            stack.append(cur)
            cur = []
            pos += 1
        elif c == ")":
            done = cur
            cur = stack.pop()
            cur.append(done)
            pos += 1
        elif c == '"':
            pos += 1
            buf = []
            while text[pos] != '"':
                if text[pos] == "\\":
                    pos += 1
                    buf.append({"n": "\n", "t": "\t"}.get(text[pos], text[pos]))
                else:
                    buf.append(text[pos])
                pos += 1
            pos += 1
            cur.append(Q("".join(buf)))
        else:
            start = pos
            while pos < n and text[pos] not in ' \t\r\n()"':
                pos += 1
            cur.append(text[start:pos])
    return cur[0]


def _atom(a):
    if isinstance(a, Q):
        return '"' + a.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if isinstance(a, float):
        s = f"{a:.4f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(a)


def dump(node, ind=0):
    if not isinstance(node, list):
        return _atom(node)
    if all(not isinstance(x, list) for x in node):
        return "(" + " ".join(_atom(x) for x in node) + ")"
    pad = "\t" * (ind + 1)
    parts = ["(" + " ".join(_atom(x) for x in node if not isinstance(x, list))]
    for x in node:
        if isinstance(x, list):
            parts.append("\n" + pad + dump(x, ind + 1))
    return "".join(parts) + "\n" + "\t" * ind + ")"


def find(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def find1(node, key):
    r = find(node, key)
    return r[0] if r else None


_libcache = {}


def load_lib(path):
    if path not in _libcache:
        with open(path, encoding="utf-8") as f:
            _libcache[path] = parse(f.read())
    return _libcache[path]


def get_symbol(lib_id, libpath=None):
    """Symbol aus Bibliothek holen, 'extends' aufloesen, fuer lib_symbols umbenennen."""
    lib, name = lib_id.split(":")
    tree = load_lib(libpath or os.path.join(SYMDIR, lib + ".kicad_sym"))
    syms = {s[1]: s for s in find(tree, "symbol")}
    sym = copy.deepcopy(syms[name])
    ext = find1(sym, "extends")
    if ext:
        parent = copy.deepcopy(syms[ext[1]])
        own_props = {p[1]: p for p in find(sym, "property")}
        out = [parent[0], Q(name)]
        for item in parent[2:]:
            if isinstance(item, list) and item[0] == "property" and item[1] in own_props:
                out.append(own_props.pop(item[1]))
            elif isinstance(item, list) and item[0] == "symbol":
                item[1] = Q(item[1].replace(ext[1], name, 1))
                out.append(item)
            else:
                out.append(item)
        # zusaetzliche Properties des Kindsymbols vor den Untersymbolen einfuegen
        idx = next(i for i, x in enumerate(out) if isinstance(x, list) and x[0] == "symbol")
        out[idx:idx] = list(own_props.values())
        sym = out
    sym[1] = Q(lib_id)
    return sym


def pins(sym):
    """Liefert {nummer: (x, y, rot, typ, name)} in Symbolkoordinaten (Y nach oben)."""
    res = {}
    for sub in find(sym, "symbol"):
        for p in find(sub, "pin"):
            at = find1(p, "at")
            num = find1(p, "number")[1]
            name = find1(p, "name")[1]
            res[str(num)] = (float(at[1]), float(at[2]), float(at[3]), p[1], str(name))
    return res
