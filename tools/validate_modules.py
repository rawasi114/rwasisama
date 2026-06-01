#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Offline validator for the Rawasi Sama Odoo modules (no Odoo install needed).

Per module it checks:
  * __manifest__.py parses to a dict with required keys
  * every file referenced in 'data' / 'demo' exists
  * every asset file referenced under 'assets' (own module) exists
  * all .py files compile (syntax)
  * all .xml files are well-formed; flags <record>/<menuitem>/<template> without id
  * security/ir.model.access.csv header + column consistency + unique ids

Exit code is non-zero if any ERROR is found (warnings do not fail).
Usage: python3 tools/validate_modules.py [module ...]
"""
import ast
import csv
import os
import py_compile
import sys

try:
    from lxml import etree
    HAVE_LXML = True
except Exception:
    import xml.etree.ElementTree as etree  # type: ignore
    HAVE_LXML = False

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIRED_MANIFEST_KEYS = ("name", "version", "depends", "license")
ACCESS_HEADER = [
    "id", "name", "model_id:id", "group_id:id",
    "perm_read", "perm_write", "perm_create", "perm_unlink",
]

errors, warnings, notices = [], [], []
def err(m): errors.append(m)
def warn(m): warnings.append(m)
def note(m): notices.append(m)


def _is_module(p):
    return os.path.isdir(p) and os.path.isfile(os.path.join(p, "__manifest__.py"))


def _discover_roots():
    """Directories that may directly contain Odoo modules: the repo root and any
    top-level ``addons``-style folder (so modules under ``addons/`` are not missed)."""
    roots = [ROOT]
    for name in sorted(os.listdir(ROOT)):
        p = os.path.join(ROOT, name)
        if os.path.isdir(p) and not _is_module(p) and name not in (".git", "docs", "tools"):
            roots.append(p)
    return roots


def find_modules(argv):
    if argv:
        out = []
        for m in argv:
            for base in _discover_roots():
                cand = os.path.join(base, m)
                if _is_module(cand):
                    out.append(cand)
                    break
            else:
                out.append(os.path.join(ROOT, m))  # report-as-missing downstream
        return out
    mods = []
    for base in _discover_roots():
        for name in sorted(os.listdir(base)):
            p = os.path.join(base, name)
            if _is_module(p):
                mods.append(p)
    return mods


def load_manifest(mod):
    name = os.path.basename(mod)
    try:
        with open(os.path.join(mod, "__manifest__.py"), encoding="utf-8") as f:
            data = ast.literal_eval(f.read())
    except Exception as exc:
        err(f"[{name}] __manifest__.py does not parse as a literal dict: {exc}")
        return None
    if not isinstance(data, dict):
        err(f"[{name}] __manifest__.py is not a dict")
        return None
    for key in REQUIRED_MANIFEST_KEYS:
        if key not in data:
            err(f"[{name}] manifest missing required key: {key!r}")
    return data


def check_referenced_files(mod, manifest):
    name = os.path.basename(mod)
    for section in ("data", "demo"):
        for rel in manifest.get(section, []) or []:
            if not os.path.isfile(os.path.join(mod, rel)):
                err(f"[{name}] manifest '{section}' references missing file: {rel}")
    for bundle, paths in (manifest.get("assets", {}) or {}).items():
        for p in paths:
            parts = p.split("/", 1)
            if len(parts) == 2 and parts[0] == name:
                if not os.path.isfile(os.path.join(mod, parts[1])):
                    err(f"[{name}] asset bundle '{bundle}' references missing file: {p}")


def check_python(mod):
    name = os.path.basename(mod)
    for dp, _d, files in os.walk(mod):
        for fn in files:
            if fn.endswith(".py"):
                fp = os.path.join(dp, fn)
                try:
                    py_compile.compile(fp, doraise=True)
                except py_compile.PyCompileError as exc:
                    err(f"[{name}] Python syntax error in {os.path.relpath(fp, mod)}: {exc.msg}")


def check_xml(mod):
    name = os.path.basename(mod)
    for dp, _d, files in os.walk(mod):
        for fn in files:
            if not fn.endswith(".xml"):
                continue
            fp = os.path.join(dp, fn)
            rel = os.path.relpath(fp, mod)
            try:
                tree = etree.parse(fp)
            except Exception as exc:
                err(f"[{name}] XML not well-formed: {rel}: {exc}")
                continue
            root = tree.getroot()
            tag = root.tag if isinstance(root.tag, str) else ""
            if tag not in ("odoo", "openerp", "data", "templates"):
                warn(f"[{name}] {rel}: unexpected XML root <{tag}>")
            for el in root.iter():
                t = el.tag if isinstance(el.tag, str) else ""
                if t in ("record", "menuitem", "template") and not el.get("id"):
                    warn(f"[{name}] {rel}: <{t}> without id attribute")


def check_access_csv(mod):
    name = os.path.basename(mod)
    fp = os.path.join(mod, "security", "ir.model.access.csv")
    if not os.path.isfile(fp):
        return
    with open(fp, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if not rows:
        err(f"[{name}] ir.model.access.csv is empty")
        return
    if [c.strip() for c in rows[0]] != ACCESS_HEADER:
        err(f"[{name}] ir.model.access.csv header mismatch: {rows[0]}")
    seen = set()
    for i, row in enumerate(rows[1:], start=2):
        if not any(c.strip() for c in row):
            continue
        if len(row) != len(ACCESS_HEADER):
            err(f"[{name}] ir.model.access.csv line {i}: {len(row)} cols (want {len(ACCESS_HEADER)})")
            continue
        rid = row[0].strip()
        if rid in seen:
            err(f"[{name}] ir.model.access.csv duplicate id: {rid}")
        seen.add(rid)


def main():
    argv = [a for a in sys.argv[1:] if not a.startswith("-")]
    mods = find_modules(argv)
    if not mods:
        print("No Odoo modules found.")
        return 1
    print(f"Validating {len(mods)} module(s); lxml={'yes' if HAVE_LXML else 'no'}\n")
    # A module's technical name is its directory name. Two modules sharing it
    # under the SAME addons-path root cannot coexist (only the first loads) -> error.
    # The same name under DIFFERENT roots is allowed on purpose: it marks two
    # mutually-exclusive deployments that must never share one addons_path -> notice.
    by_root, by_name = {}, {}
    for mod in mods:
        by_root.setdefault(os.path.dirname(mod), {}).setdefault(os.path.basename(mod), []).append(mod)
        by_name.setdefault(os.path.basename(mod), []).append(mod)
    for _root, names in sorted(by_root.items()):
        for tech_name, paths in sorted(names.items()):
            if len(paths) > 1:
                locs = ", ".join(os.path.relpath(p, ROOT) for p in paths)
                err(f"duplicate module technical name {tech_name!r} within one addons root: {locs}")
    for tech_name, paths in sorted(by_name.items()):
        if len({os.path.dirname(p) for p in paths}) > 1:
            locs = ", ".join(os.path.relpath(p, ROOT) for p in paths)
            note(f"module {tech_name!r} exists in separate deployments (never load together): {locs}")
    for mod in mods:
        m = load_manifest(mod)
        if m:
            check_referenced_files(mod, m)
        check_python(mod)
        check_xml(mod)
        check_access_csv(mod)
        print(f"  - {os.path.relpath(mod, ROOT)}: checked")
    print()
    if notices:
        print(f"NOTICES ({len(notices)}):")
        for n in notices:
            print("  i " + n)
        print()
    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print("  ! " + w)
    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for e in errors:
            print("  x " + e)
        print("\nFAILED")
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
