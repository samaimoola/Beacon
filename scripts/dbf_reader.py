"""
scripts/dbf_reader.py
=====================
Minimal, dependency-free reader for dBASE (.dbf) attribute tables — the
tabular side of a shapefile. Lets us inspect join keys, equipment identifiers,
and damage attributes WITHOUT adding geopandas/fiona/pyshp (shared deps that
would require coordination per AGENTS.md).

Supports the common field types in these files: C (char), N/F (numeric),
D (date), L (logical). Geometry (.shp) is intentionally not read here — this
milestone only needs attributes and join keys.

Owner: Samai (scripts/)

Reference: the dBASE III+/dBASE IV .dbf layout is a long-stable, public format.
"""

from __future__ import annotations
import struct
from pathlib import Path
from typing import Iterator, Optional


class DBF:
    """Lazy reader over a .dbf file."""

    def __init__(self, path: str | Path, encoding: str = "latin-1"):
        self.path = Path(path)
        self.encoding = encoding
        self.fields: list[tuple[str, str, int]] = []  # (name, type, length)
        self.n_records: int = 0
        self._header_len: int = 0
        self._record_len: int = 0
        self._read_header()

    def _read_header(self) -> None:
        with open(self.path, "rb") as f:
            header = f.read(32)
            self.n_records = struct.unpack("<I", header[4:8])[0]
            self._header_len = struct.unpack("<H", header[8:10])[0]
            self._record_len = struct.unpack("<H", header[10:12])[0]

            # Field descriptors are 32 bytes each until a 0x0D terminator.
            self.fields = []
            while True:
                desc = f.read(32)
                if not desc or desc[0:1] == b"\r":
                    break
                name = desc[0:11].split(b"\x00")[0].decode(self.encoding).strip()
                ftype = desc[11:12].decode(self.encoding)
                flen = desc[16]
                self.fields.append((name, ftype, flen))

    @property
    def field_names(self) -> list[str]:
        return [name for name, _, _ in self.fields]

    def _convert(self, value: str, ftype: str):
        value = value.strip()
        if value == "":
            return None
        if ftype in ("N", "F"):
            try:
                if "." in value:
                    return float(value)
                return int(value)
            except ValueError:
                try:
                    return float(value)
                except ValueError:
                    return None
        if ftype == "L":
            return value.upper() in ("Y", "T")
        # C (char), D (date as string), and anything else -> string
        return value

    def records(self, limit: Optional[int] = None) -> Iterator[dict]:
        """Yield records as dicts. `limit` caps how many are read."""
        with open(self.path, "rb") as f:
            f.seek(self._header_len)
            count = 0
            for _ in range(self.n_records):
                rec = f.read(self._record_len)
                if not rec or len(rec) < self._record_len:
                    break
                if rec[0:1] == b"\x1a":  # EOF marker
                    break
                deleted = rec[0:1] == b"*"
                if deleted:
                    continue
                row: dict = {}
                offset = 1  # first byte is the deletion flag
                for name, ftype, flen in self.fields:
                    raw = rec[offset:offset + flen].decode(self.encoding, errors="replace")
                    row[name] = self._convert(raw, ftype)
                    offset += flen
                yield row
                count += 1
                if limit is not None and count >= limit:
                    break


def column_summary(dbf: DBF, sample: Optional[int] = None) -> dict[str, dict]:
    """Return per-column stats: non-null count, null count, distinct sample, dtype guess.

    Does NOT print values — caller decides what to surface (avoid PII).
    """
    stats: dict[str, dict] = {
        name: {"non_null": 0, "null": 0, "distinct": set(), "ftype": ft, "length": fl}
        for name, ft, fl in dbf.fields
    }
    total = 0
    for row in dbf.records(limit=sample):
        total += 1
        for name in dbf.field_names:
            v = row[name]
            s = stats[name]
            if v is None:
                s["null"] += 1
            else:
                s["non_null"] += 1
                if len(s["distinct"]) < 50:
                    s["distinct"].add(v)
    for s in stats.values():
        s["distinct_count_sampled"] = len(s["distinct"])
    stats["__rows_read__"] = total  # type: ignore[assignment]
    return stats
