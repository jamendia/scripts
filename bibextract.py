#!/usr/bin/env python3
"""
Create a new .bib with only the entries cited in a .tex file.

Usage examples:
  python bibextract.py paper.tex master.bib -o paper-only.bib
  python bibextract.py -t paper.tex -b master.bib --sort --force

Requirements:
  pip install bibtexparser
"""
from __future__ import annotations

import argparse
import logging
from collections import OrderedDict
from pathlib import Path
from typing import Iterable, List

import re
import bibtexparser
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bwriter import BibTexWriter

LOG = logging.getLogger("bibextract")

CITE_PATTERN = re.compile(
    r'\\[A-Za-z@]*cite[A-Za-z*@]*\s*(?:\[[^\]]*\]\s*)*\{([^}]*)\}',
    flags=re.DOTALL,
)


def extract_citation_keys(tex_text: str) -> List[str]:
    """
    Extract citation keys from TeX content.

    Handles \cite, \citep, \citet, \autocite, etc., optional arguments like
    \cite[see][p.2]{key1,key2}, and multi-line commands.
    Returns keys in order of first appearance (duplicates removed).
    """
    matches = CITE_PATTERN.findall(tex_text)
    seen: OrderedDict[str, None] = OrderedDict()
    for group in matches:
        # group may contain "key1,key2" possibly with spaces
        for raw in group.split(","):
            key = raw.strip()
            if key and key not in seen:
                seen[key] = None
    return list(seen.keys())


def load_bib_database(bib_path: Path) -> BibDatabase:
    with bib_path.open(encoding="utf8") as fh:
        return bibtexparser.load(fh)


def filter_entries_by_keys(entries: Iterable[dict], keys: Iterable[str]) -> List[dict]:
    key_set = set(keys)
    filtered = []
    for entry in entries:
        # bibtexparser uses 'ID' as the key name
        entry_id = entry.get("ID") or entry.get("id")
        if entry_id in key_set:
            filtered.append(entry)
    return filtered


def write_bib(entries: List[dict], out_path: Path, sort: bool = False) -> None:
    db = BibDatabase()
    if sort:
        entries = sorted(entries, key=lambda e: (e.get("ID") or e.get("id")).lower())
    db.entries = entries
    writer = BibTexWriter()
    writer.indent = "  "
    writer.order_entries_by = None  # preserve order unless we sorted above
    with out_path.open("w", encoding="utf8", newline="\n") as fh:
        fh.write(writer.write(db))


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Extract cited BibTeX entries from a TeX file.")
    p.add_argument("tex", type=Path, help="Path to TeX file")
    p.add_argument("bib", type=Path, help="Path to master BibTeX (.bib) file")
    p.add_argument("-o", "--output", type=Path, default=None, help="Output .bib file (default: <tex-stem>-extracted.bib)")
    p.add_argument("-s", "--sort", action="store_true", help="Sort entries alphabetically by key in the output")
    p.add_argument("-f", "--force", action="store_true", help="Overwrite output file if it exists")
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s")

    if not args.tex.exists():
        LOG.error("TeX file not found: %s", args.tex)
        return 2
    if not args.bib.exists():
        LOG.error("Bib file not found: %s", args.bib)
        return 2

    tex_text = args.tex.read_text(encoding="utf8")
    keys = extract_citation_keys(tex_text)
    if not keys:
        LOG.warning("No citation keys found in %s", args.tex)
        return 0
    LOG.info("Found %d unique citation keys", len(keys))

    bib_db = load_bib_database(args.bib)
    matched = filter_entries_by_keys(bib_db.entries, keys)

    found_keys = {(e.get("ID") or e.get("id")) for e in matched}
    missing = [k for k in keys if k not in found_keys]
    LOG.info("Matched %d entries; %d keys missing from the .bib", len(matched), len(missing))
    if missing:
        LOG.warning("Missing keys: %s", ", ".join(missing[:10]) + ("..." if len(missing) > 10 else ""))

    out_path = args.output or args.tex.with_suffix(".extracted.bib")
    if out_path.exists() and not args.force:
        LOG.error("Output file already exists (%s). Use --force to overwrite.", out_path)
        return 3

    # Preserve order of appearance by default
    entries_in_order = []
    key_to_entry = {e.get("ID") or e.get("id"): e for e in bib_db.entries}
    for k in keys:
        if k in key_to_entry:
            entries_in_order.append(key_to_entry[k])

    # Fallback: include any matched entries that for some reason didn't appear in the ordered list
    extra = [e for e in matched if (e.get("ID") or e.get("id")) not in {x.get("ID") or x.get("id") for x in entries_in_order}]
    entries_in_order.extend(extra)

    write_bib(entries_in_order, out_path, sort=args.sort)
    LOG.info("Wrote %d entries to %s", len(entries_in_order), out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
