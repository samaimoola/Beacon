"""
scripts/xlsx_reader.py
======================
Minimal, dependency-free reader for .xlsx workbooks. An .xlsx is a zip of XML
parts; we read sheets with the standard library (zipfile + ElementTree) so we
do not need to add openpyxl (a shared dependency requiring coordination).

Reads cell values (shared strings + inline/number cells). Formatting, formulas
(returns cached value if present), and styles are ignored.

Owner: Samai (scripts/)
"""

from __future__ import annotations
import zipfile
import re
from pathlib import Path
from xml.etree import ElementTree as ET

_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _col_to_index(cell_ref: str) -> int:
    """Convert an A1-style column (e.g. 'B7' -> 1, 0-indexed)."""
    letters = re.match(r"[A-Z]+", cell_ref).group(0)
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


class XLSX:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._zip = zipfile.ZipFile(self.path)
        self._shared = self._read_shared_strings()
        self.sheets = self._read_sheet_names()

    def _read_shared_strings(self) -> list[str]:
        try:
            data = self._zip.read("xl/sharedStrings.xml")
        except KeyError:
            return []
        root = ET.fromstring(data)
        out: list[str] = []
        for si in root.findall("m:si", _NS):
            # Concatenate all text runs within a shared-string item
            text = "".join(t.text or "" for t in si.iter("{%s}t" % _NS["m"]))
            out.append(text)
        return out

    def _read_sheet_names(self) -> dict[str, str]:
        """Return {sheet_name: internal_path}."""
        wb = ET.fromstring(self._zip.read("xl/workbook.xml"))
        rels = ET.fromstring(self._zip.read("xl/_rels/workbook.xml.rels"))
        rid_to_target = {
            r.get("Id"): r.get("Target")
            for r in rels
        }
        names: dict[str, str] = {}
        rns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        for sheet in wb.find("m:sheets", _NS):
            name = sheet.get("name")
            rid = sheet.get(rns)
            target = rid_to_target.get(rid, "")
            if not target.startswith("xl/"):
                target = "xl/" + target.lstrip("/")
            names[name] = target
        return names

    def rows(self, sheet_name: str) -> list[list]:
        """Return the sheet as a list of rows (list of cell values)."""
        path = self.sheets[sheet_name]
        root = ET.fromstring(self._zip.read(path))
        sheet_data = root.find("m:sheetData", _NS)
        result: list[list] = []
        for row in sheet_data.findall("m:row", _NS):
            cells: dict[int, object] = {}
            max_c = -1
            for c in row.findall("m:c", _NS):
                ref = c.get("r", "A1")
                col = _col_to_index(ref)
                max_c = max(max_c, col)
                ctype = c.get("t")
                v = c.find("m:v", _NS)
                if ctype == "s":  # shared string
                    val = self._shared[int(v.text)] if v is not None else None
                elif ctype == "inlineStr":
                    is_ = c.find("m:is", _NS)
                    val = "".join(t.text or "" for t in is_.iter("{%s}t" % _NS["m"])) if is_ is not None else None
                else:  # number / general
                    if v is None:
                        val = None
                    else:
                        try:
                            val = float(v.text)
                            if val.is_integer():
                                val = int(val)
                        except ValueError:
                            val = v.text
                cells[col] = val
            row_list = [cells.get(i) for i in range(max_c + 1)]
            result.append(row_list)
        return result
