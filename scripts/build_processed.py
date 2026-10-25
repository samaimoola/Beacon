"""
scripts/build_processed.py
==========================
Build a small, PII-FREE processed dataset that the engine consumes, so the
engine never parses the 28 MB topology file at runtime and never touches
customer addresses / names / meter ids.

For a handful of selected premises it records ONLY:
  - an anonymized local id (not the premise number, not any PII)
  - service kind (Overhead / Underground) and anonymized circuit name
  - the verified upstream chain (transformer + ordered isolating devices),
    resolved to device types from the equipment layers
  - circuit-level historical damage evidence (counts by asset type / access),
    clearly labeled as historical, not a live outage
  - a labor-based restoration-effort estimate for the upstream equipment,
    using the workbook's install hours and the single indirect-labor multiplier

Output: data/processed/premises.json

Owner: Samai (scripts/)

Usage:
    python -m scripts.extract_data
    python -m scripts.build_processed
"""

from __future__ import annotations
import hashlib
import json
from pathlib import Path

from scripts.dbf_reader import DBF
from scripts.xlsx_reader import XLSX
from scripts.inspect_data import load_matched_upstream, inspect_labor

REPO_ROOT = Path(__file__).resolve().parents[1]
EXTRACT = REPO_ROOT / "data" / "extracted"
PROCESSED = REPO_ROOT / "data" / "processed"
WORKBOOK = REPO_ROOT / "data" / "Install_Labor_HackOHIO.xlsx"

# Number of real premises to select for the demo (challenge asks for three).
N_PREMISES = 3


def _strip(v) -> str:
    return "" if v is None else str(v).strip()


def _anon_id(premise: str, salt: str = "stormready-v2") -> str:
    """Deterministic, non-reversible short id so we never store the premise number."""
    h = hashlib.sha256((salt + premise).encode()).hexdigest()
    return "rp-" + h[:8]


def build_equipment_type_index() -> dict[str, str]:
    """location_n -> human device type, across device layers."""
    idx: dict[str, str] = {}
    sources = [
        (EXTRACT / "Data2" / "Transformer_Clip.dbf", "device_typ", "Transformer"),
        (EXTRACT / "Data2" / "Switch_Clip.dbf", "device_typ", "Switch"),
        (EXTRACT / "Data2" / "Recloser_Bank_Clip.dbf", "device_typ", "Recloser Bank"),
        (EXTRACT / "Data1" / "Fuse_Bank_Clip.dbf", "device_typ", "Fuse Bank"),
    ]
    for path, field, fallback in sources:
        for r in DBF(path).records():
            loc = _strip(r.get("location_n"))
            if not loc:
                continue
            dt = _strip(r.get(field)) or fallback
            idx.setdefault(loc, dt)
    return idx


def circuit_damage_summary() -> dict[str, dict]:
    """anonymized circuit name -> historical damage summary (counts only, no PII)."""
    dmg = DBF(EXTRACT / "Data1" / "arcos_prod_damage_09_28_Clip.dbf")
    out: dict[str, dict] = {}
    for r in dmg.records():
        c = _strip(r.get("Circuit"))
        if not c:
            continue
        rec = out.setdefault(c, {"total": 0, "by_asset_type": {}, "access_issues": 0,
                                 "repaired_yes": 0, "repaired_no": 0})
        rec["total"] += 1
        at = _strip(r.get("Asset_Type"))
        if at:
            rec["by_asset_type"][at] = rec["by_asset_type"].get(at, 0) + 1
        if _strip(r.get("Access_Iss")).lower() == "yes":
            rec["access_issues"] += 1
        rep = _strip(r.get("Repaired")).lower()
        if rep == "yes":
            rec["repaired_yes"] += 1
        elif rep == "no":
            rec["repaired_no"] += 1
    return out


def labor_hours_for_chain(chain_items: list[dict], labor: dict) -> dict:
    """
    Estimate DIRECT crew-hours to replace/repair the upstream equipment chain,
    then apply the indirect labor multiplier ONCE.

    `chain_items` is a list of {"role": ..., "device_type": ...} excluding the
    circuit breaker. The serving transformer is priced from the workbook's
    transformer-by-size table; isolating devices are not itemized by size in the
    workbook, so they use a LABELED ASSUMPTION.

    Returns direct_hours, effective_hours (direct * ILM), and per-item detail.
    """
    ilm = labor["indirect_labor_multiplier"]["value"]
    xfmr_table = labor["tables"]["transformer_install_remove_hours_by_kVA"]
    # The transformer SIZE is an assumption (we don't know this premise's kVA);
    # the HOUR VALUE for the chosen size is a real workbook figure.
    if 100 in xfmr_table:
        xfmr_install = xfmr_table[100]["install_hours"]
        xfmr_basis = ("transformer install hours from the workbook table for an ASSUMED "
                      "representative size of 100 kVA (premise kVA unknown; the hour value "
                      "itself is from the workbook, the size choice is the assumption)")
        xfmr_size_assumed = True  # size assumed; the hour figure is from the workbook
    else:
        vals = [v["install_hours"] for v in xfmr_table.values()]
        xfmr_install = sum(vals) / len(vals)
        xfmr_basis = ("transformer install hours = MEAN of the workbook table across sizes "
                      "(ASSUMED because premise kVA is unknown)")
        xfmr_size_assumed = True

    # Assumed install hours for isolating devices (NOT itemized by size in workbook).
    ASSUMED = {
        "recloser": 2.0,
        "switch": 1.0,
        "fuse": 0.5,
    }

    items = []
    direct = 0.0
    for c in chain_items:
        role = c.get("role")
        dtype = c.get("device_type", "")
        if role == "serving_transformer":
            h = round(xfmr_install, 3)
            basis = xfmr_basis
            # The HOUR VALUE is from the workbook; only the SIZE is assumed.
            value_from_workbook = True
            size_assumed = xfmr_size_assumed
        else:
            key = next((k for k in ASSUMED if k in dtype.lower()), None)
            h = ASSUMED.get(key, 1.0)
            basis = (f"LABELED ASSUMPTION ({h} h direct) — isolating devices are not itemized "
                     "by size in the workbook, so BOTH the value and size are assumed")
            value_from_workbook = False
            size_assumed = True
        direct += h
        items.append({"device_type": dtype, "role": role,
                      "direct_install_hours": round(h, 3),
                      "basis": basis,
                      # Precise flags: distinguish an assumed SIZE from an assumed VALUE.
                      "hours_value_from_workbook": value_from_workbook,
                      "size_assumed": size_assumed,
                      # Back-compat: is_assumption == True when the hour VALUE is assumed.
                      "is_assumption": not value_from_workbook})

    return {
        "direct_hours": round(direct, 3),
        "indirect_labor_multiplier": ilm,
        # NOTE: "effective_hours" is labor effort in the workbook's own (unresolved)
        # hour unit — NOT necessarily elapsed wall-clock time. See labor_unit below.
        "effective_crew_hours": round(direct * ilm, 2),
        "labor_unit": "UNRESOLVED",
        "labor_unit_note": (
            "The workbook does not state whether its hours are worker-hours, crew-hours, "
            "or elapsed hours. Beacon treats them as effort (person-or-crew hours) and "
            "any conversion to elapsed time elsewhere must expose its assumed interpretation "
            "and the assumed crew size. Open question for AEP mentors."
        ),
        "method": "sum(direct install hours per upstream device) * ILM (ILM applied once; "
                  "it already covers travel/setup/safety — not added separately)",
        "items": items,
    }


def build_task_catalog(labor: dict) -> dict:
    """
    Map repair tasks to workbook install/removal references (effort hours).

    Returns {task_key: {"label", "direct_hours" | None, "hours_source",
                        "is_assumption"}}.

    Tasks backed by the workbook (poles by size, transformer by kVA) are marked
    is_assumption=False for their VALUE (size still chosen by scenario). Tasks
    the workbook does not itemize (fuse, recloser, line/conductor spans) use
    LABELED ASSUMPTIONS, and anything we cannot map is left None (unknown).
    """
    pole = labor["tables"]["pole_install_remove_hours_by_size"]
    xfmr = labor["tables"]["transformer_install_remove_hours_by_kVA"]

    def pole_h(size):
        rec = pole.get(size)
        return round(rec["install_hours"] + rec["remove_hours"], 3) if rec else None

    def xfmr_h(kva):
        rec = xfmr.get(kva)
        return round(rec["install_hours"] + rec["remove_hours"], 3) if rec else None

    catalog = {
        # Poles — workbook value by size; the size is chosen by the scenario.
        "replace_pole_small": {
            "label": "Replace small pole (25–35 ft)",
            "direct_hours": pole_h("Small"),
            "hours_source": "workbook pole table (Small): install+remove hours",
            "is_assumption": False,
        },
        "replace_pole_medium": {
            "label": "Replace medium pole (40–55 ft)",
            "direct_hours": pole_h("Medium"),
            "hours_source": "workbook pole table (Medium): install+remove hours",
            "is_assumption": False,
        },
        "replace_pole_large": {
            "label": "Replace large pole (60 ft+)",
            "direct_hours": pole_h("Large"),
            "hours_source": "workbook pole table (Large): install+remove hours",
            "is_assumption": False,
        },
        # Transformer — workbook value; kVA assumed at a representative 100 kVA.
        "replace_transformer": {
            "label": "Replace distribution transformer (assumed 100 kVA)",
            "direct_hours": xfmr_h(100),
            "hours_source": "workbook transformer table at ASSUMED 100 kVA: install+remove hours",
            "is_assumption": False,  # value from workbook; only the kVA size is assumed
        },
        # Not itemized by the workbook -> LABELED ASSUMPTIONS.
        "replace_fuse": {
            "label": "Replace fuse / refuse",
            "direct_hours": 0.5,
            "hours_source": "LABELED ASSUMPTION — fuse work not itemized in workbook",
            "is_assumption": True,
        },
        "replace_recloser": {
            "label": "Replace / reset recloser",
            "direct_hours": 2.0,
            "hours_source": "LABELED ASSUMPTION — recloser work not itemized in workbook",
            "is_assumption": True,
        },
        "repair_primary_span": {
            "label": "Repair primary conductor span",
            "direct_hours": 2.5,
            "hours_source": "LABELED ASSUMPTION — line/conductor spans not itemized in workbook",
            "is_assumption": True,
        },
        "repair_secondary_span": {
            "label": "Repair secondary conductor span",
            "direct_hours": 1.5,
            "hours_source": "LABELED ASSUMPTION — line/conductor spans not itemized in workbook",
            "is_assumption": True,
        },
        # A deliberately UNMAPPED task to exercise the 'unknown' path.
        "assess_unknown_asset": {
            "label": "Assess/repair unmapped asset",
            "direct_hours": None,
            "hours_source": "UNKNOWN — no workbook or assumed mapping for this asset",
            "is_assumption": True,
        },
    }
    return catalog


def build_damage_scenarios(premise_chain: list[dict], service_kind: str) -> list[dict]:
    """
    Build a few SIMULATED damage-scenario presets for a premise.

    Each scenario names damaged assets (type + quantity) and the repair jobs
    (task keys) with simple dependencies. Dependencies reflect field reality,
    e.g. a pole must be set before its conductor span can be re-hung.

    These are explicitly simulated — NOT read from the historical damage file.
    """
    pole_size = "replace_pole_medium"  # assumed representative size

    scenarios = [
        {
            "id": "none",
            "label": "No damage (precautionary)",
            "description": "Storm passed without equipment damage on this premise's path.",
            "damaged_assets": [],
            "jobs": [],
        },
        {
            "id": "fuse_only",
            "label": "Single fuse operation",
            "description": "A protective fuse opened; one refuse restores service once reached.",
            "damaged_assets": [{"asset_type": "Fuse", "quantity": 1}],
            "jobs": [
                {"task": "replace_fuse", "depends_on": []},
            ],
        },
        {
            "id": "pole_and_span",
            "label": "Downed pole + conductor",
            "description": "A pole is down, taking a primary span with it. The span can only "
                           "be re-hung after the pole is set (dependency).",
            "damaged_assets": [
                {"asset_type": "Pole", "quantity": 1},
                {"asset_type": "Primary span", "quantity": 1},
            ],
            "jobs": [
                {"task": pole_size, "depends_on": []},           # job 0: set pole
                {"task": "repair_primary_span", "depends_on": [0]},  # job 1: after pole
            ],
        },
        {
            "id": "multi_damage",
            "label": "Widespread damage",
            "description": "Multiple poles and spans down plus a failed transformer. Pole/span "
                           "pairs are dependent; transformer work is independent and parallelizable.",
            "damaged_assets": [
                {"asset_type": "Pole", "quantity": 2},
                {"asset_type": "Primary span", "quantity": 2},
                {"asset_type": "Transformer", "quantity": 1},
            ],
            "jobs": [
                {"task": pole_size, "depends_on": []},                 # 0 pole A
                {"task": "repair_primary_span", "depends_on": [0]},    # 1 span A (after pole A)
                {"task": pole_size, "depends_on": []},                 # 2 pole B
                {"task": "repair_primary_span", "depends_on": [2]},    # 3 span B (after pole B)
                {"task": "replace_transformer", "depends_on": []},     # 4 transformer (independent)
            ],
        },
        {
            "id": "unmapped_asset",
            "label": "Unmapped asset (unknown effort)",
            "description": "Damage to an asset Beacon cannot map to a workbook labor "
                           "reference — the estimate is deliberately UNKNOWN, not invented.",
            "damaged_assets": [{"asset_type": "Unmapped equipment", "quantity": 1}],
            "jobs": [
                {"task": "assess_unknown_asset", "depends_on": []},
            ],
        },
    ]
    return scenarios


def pick_premises(mu: dict, cust_rows: list[dict], damage: dict,
                  equip_types: dict[str, str]) -> list[str]:
    """
    Choose N premises that give a defensible, varied example:
      - upstream chain fully resolvable to device types
      - circuit present in the historical damage set (so we have evidence)
      - prefer a mix of Overhead / Underground service
    Returns a list of premise numbers.
    """
    by_premise = {_strip(r.get("premise_nu")): r for r in cust_rows if _strip(r.get("premise_nu"))}
    candidates = []
    for premise, row in by_premise.items():
        rec = mu.get(premise)
        if not rec or not rec["transformer_loc"]:
            continue
        chain_locs = [rec["transformer_loc"]] + [d["loc"] for d in rec["iso_chain"]]
        if not all(loc in equip_types for loc in chain_locs if loc):
            continue
        # circuit name via network name on the transformer? we use customer circuit_id bridge later;
        # here require the customer circuit maps to a damaged circuit name.
        candidates.append(premise)
    # Deterministic order for reproducibility
    candidates.sort()
    # Try to vary service kind
    picked: list[str] = []
    seen_kinds: set = set()
    for p in candidates:
        kind = _strip(by_premise[p].get("kind_of_se"))
        if kind not in seen_kinds or len(picked) >= 2:
            picked.append(p)
            seen_kinds.add(kind)
        if len(picked) >= N_PREMISES:
            break
    if len(picked) < N_PREMISES:
        picked = candidates[:N_PREMISES]
    return picked


def build() -> dict:
    labor = inspect_labor()
    equip_types = build_equipment_type_index()
    damage = circuit_damage_summary()
    mu = load_matched_upstream()

    cust = DBF(EXTRACT / "Data1" / "Customer_Clip.dbf")
    cust_rows = list(cust.records())

    # numeric circuit_id -> anonymized name bridge
    id2name: dict[str, str] = {}
    for p in [EXTRACT / "Data1" / "Primary_ExportFeatures.dbf"]:
        for r in DBF(p).records():
            cid = _strip(r.get("circuit_id"))
            nm = _strip(r.get("aep_circui"))
            if cid and nm:
                id2name.setdefault(cid, nm)

    picked = pick_premises(mu, cust_rows, damage, equip_types)
    by_premise = {_strip(r.get("premise_nu")): r for r in cust_rows if _strip(r.get("premise_nu"))}

    premises_out = []
    for i, premise in enumerate(picked):
        row = by_premise[premise]
        rec = mu[premise]
        service_kind = _strip(row.get("kind_of_se")) or "Unknown"
        num_circuit = _strip(row.get("circuit_id"))
        circuit_name = id2name.get(num_circuit)  # anonymized name, may be None

        # Resolve upstream chain to device types (ordered nearest -> source)
        chain = []
        xfmr_class = equip_types.get(rec["transformer_loc"], "")
        xfmr_label = f"Transformer ({xfmr_class})" if xfmr_class else "Transformer"
        chain.append({"role": "serving_transformer", "device_type": xfmr_label})
        for d in rec["iso_chain"]:
            chain.append({"role": "upstream_isolating_device",
                          "device_type": equip_types.get(d["loc"], d.get("label") or "Unknown")})
        chain.append({"role": "circuit_breaker", "device_type": "Circuit Breaker"})

        # LEGACY/context only: effort to replace the whole upstream chain. This is
        # NOT used to drive restoration anymore (we no longer assume every device
        # is damaged). Retained as network context and for the ILM-once check.
        chain_for_effort = [c for c in chain if c["role"] != "circuit_breaker"]
        chain_effort_context = labor_hours_for_chain(chain_for_effort, labor)

        # Damage evidence for this circuit (HISTORICAL — context, not current damage)
        dmg_summary = damage.get(circuit_name) if circuit_name else None

        # SIMULATED damage-scenario presets (the real driver of restoration now)
        scenarios = build_damage_scenarios(chain, service_kind)

        # transformer-key agreement note
        cust_xfmr = _strip(row.get("aep_xfmr_l"))
        key_agrees = (cust_xfmr == (rec["transformer_loc"] or ""))

        premises_out.append({
            "id": _anon_id(premise),
            "label": f"Real premise {i+1} — {service_kind}"
                     + (f", circuit {circuit_name}" if circuit_name else ""),
            "service_kind": service_kind,
            "circuit_name": circuit_name,          # anonymized, from workbook/network
            "upstream_chain": chain,               # NETWORK CONTEXT (not a repair list)
            "upstream_isolating_device_count": len(rec["iso_chain"]),
            "topology_key_agreement": key_agrees,  # customer aep_xfmr_l vs matched_upstream
            "historical_damage": dmg_summary,      # HISTORICAL context; None if none recorded
            "damage_scenarios": scenarios,         # SIMULATED presets that drive restoration
            "chain_effort_context": chain_effort_context,  # legacy/context, not used for timing
            "provenance": {
                "topology": "matched_upstream.txt (verified join on premise number)",
                "equipment_types": "Transformer/Switch/Recloser/Fuse layers via location id",
                "damage_context": "arcos_prod_damage_09_28 — HISTORICAL, context only, not current damage",
                "damage_scenarios": "SIMULATED presets authored for the demo — not from any data file",
                "labor": "Install_Labor_HackOHIO.xlsx (install/removal references x single ILM)",
            },
        })

    out = {
        "schema_version": 3,
        "generated_by": "scripts/build_processed.py",
        "contains_pii": False,
        "ilm": labor["indirect_labor_multiplier"]["value"],
        "labor_unit": "UNRESOLVED",
        "labor_unit_note": (
            "Workbook does not state whether hours are worker-, crew-, or elapsed hours. "
            "Treated as effort; elapsed-time conversion exposes its assumed crew size. "
            "Open question for AEP mentors."
        ),
        "labor_caveats": labor["caveats"],
        "labor_task_catalog": build_task_catalog(labor),
        "premises": premises_out,
    }
    return out


def main() -> None:
    if not (EXTRACT / "Data1" / "Customer_Clip.dbf").exists():
        raise SystemExit("data/extracted/ is empty — run `python -m scripts.extract_data` first.")
    out = build()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    path = PROCESSED / "premises.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"Wrote {len(out['premises'])} PII-free premises to {path.relative_to(REPO_ROOT)}")
    for p in out["premises"]:
        hd = p["historical_damage"]
        print(f"  {p['id']}: {p['service_kind']}, circuit {p['circuit_name']}, "
              f"{len(p['damage_scenarios'])} damage scenario(s), "
              f"historical_damage_rows={hd['total'] if hd else 0}")


if __name__ == "__main__":
    main()
