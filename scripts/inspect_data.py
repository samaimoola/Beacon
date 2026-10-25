"""
scripts/inspect_data.py
=======================
Reproducible inspection of the supplied challenge archives and labor workbook.

Verifies and reports (WITHOUT printing personal information):
  - Customer -> topology join key (premise number) and its match rate.
  - Equipment identifiers (location ids) across matched_upstream and device layers.
  - Upstream ordering (isolating-device chain length per premise).
  - Damage -> circuit / equipment relationships (via anonymized circuit name).
  - Labor workbook structure, units, the indirect labor multiplier, and the
    double-counting caveat.

Outputs a machine-readable summary to data/processed/inspection_report.json and
prints a human-readable summary.

Owner: Samai (scripts/)

Usage:
    python -m scripts.extract_data      # once, to populate data/extracted/
    python -m scripts.inspect_data
"""

from __future__ import annotations
import json
from pathlib import Path

from scripts.dbf_reader import DBF
from scripts.xlsx_reader import XLSX

REPO_ROOT = Path(__file__).resolve().parents[1]
EXTRACT = REPO_ROOT / "data" / "extracted"
PROCESSED = REPO_ROOT / "data" / "processed"
WORKBOOK = REPO_ROOT / "data" / "Install_Labor_HackOHIO.xlsx"

# ---- fields considered safe to aggregate (NEVER address / name / meter) ----
# We only ever report counts and rates, never individual PII values.


def _strip(v) -> str:
    return "" if v is None else str(v).strip()


def load_matched_upstream() -> dict[str, dict]:
    """Parse matched_upstream.txt into {premise: {transformer_loc, iso_chain, circuit}}."""
    path = EXTRACT / "matched_upstream" / "matched_upstream.txt"
    out: dict[str, dict] = {}
    with open(path, "r", encoding="latin-1") as f:
        for line in f:
            toks = line.rstrip("\r\n").split("\t")
            if len(toks) < 2:
                continue
            premise = toks[0].strip()
            rec = {"transformer_loc": None, "iso_chain": [], "circuit": None}
            for t in toks[1:]:
                parts = t.split("*")
                kind = parts[0]
                loc = parts[3] if len(parts) >= 4 else None
                label = parts[2] if len(parts) >= 3 else None
                if kind == "eo_power_xfrmr_inst":
                    rec["transformer_loc"] = loc
                elif kind == "eo_isolating_eqpt_inst":
                    rec["iso_chain"].append({"loc": loc, "label": label})
                elif kind == "eo_circuit":
                    rec["circuit"] = loc  # numeric circuit id e.g. 0000027
            out[premise] = rec
    return out


def equipment_locations() -> dict[str, set]:
    """Location-id sets per device layer (field location_n)."""
    layers = {
        "transformer": EXTRACT / "Data2" / "Transformer_Clip.dbf",
        "switch": EXTRACT / "Data2" / "Switch_Clip.dbf",
        "recloser": EXTRACT / "Data2" / "Recloser_Bank_Clip.dbf",
        "fuse": EXTRACT / "Data1" / "Fuse_Bank_Clip.dbf",
    }
    result: dict[str, set] = {}
    for name, p in layers.items():
        s = set()
        for r in DBF(p).records():
            v = _strip(r.get("location_n"))
            if v:
                s.add(v)
        result[name] = s
    return result


def inspect() -> dict:
    report: dict = {"relationships": {}, "labor": {}, "unresolved": []}

    # --- Customers ---
    cust = DBF(EXTRACT / "Data1" / "Customer_Clip.dbf")
    cust_premise_to_xfmr: dict[str, str] = {}
    cust_premise_to_circuit: dict[str, str] = {}
    cust_service_kind: dict[str, int] = {}
    n_customers = 0
    for r in cust.records():
        n_customers += 1
        p = _strip(r.get("premise_nu"))
        if p:
            cust_premise_to_xfmr[p] = _strip(r.get("aep_xfmr_l"))
            cust_premise_to_circuit[p] = _strip(r.get("circuit_id"))
        k = _strip(r.get("kind_of_se"))
        if k:
            cust_service_kind[k] = cust_service_kind.get(k, 0) + 1

    mu = load_matched_upstream()
    cust_premises = set(cust_premise_to_xfmr.keys())
    mu_premises = set(mu.keys())

    # Premise join rate
    joined = cust_premises & mu_premises
    report["relationships"]["premise_join"] = {
        "customers_total": n_customers,
        "customers_with_premise": len(cust_premises),
        "matched_upstream_rows": len(mu_premises),
        "customers_joined_to_topology": len(joined),
        "customer_join_rate_pct": round(100 * len(joined) / len(cust_premises), 2),
        "customers_missing_topology": len(cust_premises - mu_premises),
    }

    # Transformer-location agreement
    agree = disagree = 0
    for p in joined:
        cx = cust_premise_to_xfmr.get(p, "")
        mx = mu[p]["transformer_loc"]
        if mx is None:
            continue
        if cx == mx:
            agree += 1
        else:
            disagree += 1
    report["relationships"]["customer_transformer_key"] = {
        "field_customer": "aep_xfmr_l",
        "field_topology": "eo_power_xfrmr_inst location id",
        "agree": agree,
        "disagree": disagree,
        "agreement_rate_pct": round(100 * agree / (agree + disagree), 2) if (agree + disagree) else None,
    }

    # Equipment identifiers
    eq = equipment_locations()
    all_equip = set().union(*eq.values())
    mu_xfmr_locs = {r["transformer_loc"] for r in mu.values() if r["transformer_loc"]}
    mu_iso_locs = {d["loc"] for r in mu.values() for d in r["iso_chain"] if d["loc"]}
    report["relationships"]["equipment_identifiers"] = {
        "join_field": "location_n (device) == location id (matched_upstream)",
        "mu_transformer_locs": len(mu_xfmr_locs),
        "mu_transformer_in_layer_pct": round(100 * len(mu_xfmr_locs & eq["transformer"]) / len(mu_xfmr_locs), 2),
        "mu_isolating_locs": len(mu_iso_locs),
        "mu_isolating_in_any_layer_pct": round(100 * len(mu_iso_locs & all_equip) / len(mu_iso_locs), 2),
        "device_counts": {k: len(v) for k, v in eq.items()},
    }

    # Upstream ordering
    chain_lengths = [len(r["iso_chain"]) for r in mu.values()]
    chain_lengths.sort()
    n = len(chain_lengths)
    report["relationships"]["upstream_ordering"] = {
        "note": "iso_chain is ordered nearest->source (transformer, then isolating devices, then circuit breaker)",
        "isolating_devices_per_premise_min": min(chain_lengths),
        "isolating_devices_per_premise_max": max(chain_lengths),
        "isolating_devices_per_premise_mean": round(sum(chain_lengths) / n, 2),
        "isolating_devices_per_premise_median": chain_lengths[n // 2],
        "premises_with_zero_isolating_devices": sum(1 for c in chain_lengths if c == 0),
    }

    # Damage -> circuit (anonymized name)
    dmg = DBF(EXTRACT / "Data1" / "arcos_prod_damage_09_28_Clip.dbf")
    dmg_circuits: set = set()
    asset_types: dict[str, int] = {}
    access_issue: dict[str, int] = {}
    repaired: dict[str, int] = {}
    dmg_rows = 0
    for r in dmg.records():
        dmg_rows += 1
        c = _strip(r.get("Circuit"))
        if c:
            dmg_circuits.add(c)
        for fld, store in [("Asset_Type", asset_types), ("Access_Iss", access_issue), ("Repaired", repaired)]:
            v = _strip(r.get(fld))
            if v:
                store[v] = store.get(v, 0) + 1

    # network anonymized circuit names + numeric->name bridge
    net_names: set = set()
    id2name: dict[str, set] = {}
    for p in [EXTRACT / "Data1" / "Primary_ExportFeatures.dbf",
              EXTRACT / "Data2" / "Transformer_Clip.dbf",
              EXTRACT / "Data1" / "Fuse_Bank_Clip.dbf"]:
        d = DBF(p)
        for r in d.records():
            nm = _strip(r.get("aep_circui"))
            cid = _strip(r.get("circuit_id"))
            if nm:
                net_names.add(nm)
            if nm and cid:
                id2name.setdefault(cid, set()).add(nm)

    dmg_matched = dmg_circuits & net_names
    report["relationships"]["damage_to_circuit"] = {
        "join_field": "damage.Circuit == network.aep_circui (anonymized circuit name)",
        "damage_rows": dmg_rows,
        "distinct_damage_circuits": len(dmg_circuits),
        "damage_circuits_matched_to_network": len(dmg_matched),
        "match_rate_pct": round(100 * len(dmg_matched) / len(dmg_circuits), 2),
        "unmatched_circuit_labels": sorted(dmg_circuits - net_names),
        "asset_type_counts": dict(sorted(asset_types.items(), key=lambda x: -x[1])),
        "access_issue_counts": access_issue,
        "repaired_counts": repaired,
        "numeric_circuit_id_to_name": {
            "ids": len(id2name),
            "ids_mapping_to_single_name": sum(1 for v in id2name.values() if len(v) == 1),
        },
        "evidence_nature": "HISTORICAL damage assessment (file arcos_prod_damage_09_28) — NOT a live/confirmed current outage.",
    }

    # Service kind distribution (aggregate only)
    report["relationships"]["customer_service_kind"] = cust_service_kind

    # --- Labor workbook ---
    report["labor"] = inspect_labor()

    # --- Unresolved questions for mentors ---
    report["unresolved"] = [
        f"{disagree} premises have a customer aep_xfmr_l that disagrees with the matched_upstream "
        f"transformer location id — need rule for which is authoritative.",
        f"{report['relationships']['premise_join']['customers_missing_topology']} customers have a "
        f"premise not present in matched_upstream — are these unmapped, or served by excluded assets?",
        f"Damage circuits not matched to network: {sorted(dmg_circuits - net_names)} "
        f"(look like facility names, not distribution circuits) — confirm they are out of scope.",
        f"{report['relationships']['upstream_ordering']['premises_with_zero_isolating_devices']} premises "
        f"have zero isolating devices between transformer and circuit breaker — confirm this is valid "
        f"(direct-from-breaker) rather than missing data.",
        "Damage Asset_Type values (primary/secondary/Pole/Fuse Bank/Transformer/Recloser Bank) are not "
        "keyed to a specific asset id in the damage table itself; spatial NEAR_FID links to a feature "
        "id whose layer is not labeled. Confirm the intended damage->specific-asset join.",
        "Labor 'per cubic foot' excavation adders (Manual Excavation 1.5, Difficult Excavation 4.0) have "
        "no volume provided in storm context — treated as unknown unless a volume is supplied.",
    ]

    return report


def inspect_labor() -> dict:
    wb = XLSX(WORKBOOK)
    out: dict = {"sheets": list(wb.sheets.keys()), "units": {}, "tables": {}, "caveats": []}

    # Indirect Labor Multiplier
    ilm_rows = wb.rows("Indirect Labor Multiplier")
    ilm_value = None
    ilm_note = None
    for row in ilm_rows:
        if row and isinstance(row[0], str) and "multipl" in row[0].lower() and len(row) > 1 and isinstance(row[1], (int, float)):
            ilm_value = float(row[1])
        elif row and isinstance(row[0], str) and "drive time" in row[0].lower():
            ilm_note = row[0]
    out["indirect_labor_multiplier"] = {
        "value": ilm_value,
        "covers": "drive time, safety discussion time, set up time (per workbook note)",
        "note": ilm_note,
    }

    # Pole install/remove by size (from 'Labor time material related')
    lm = wb.rows("Labor time material related")
    pole_table = {}
    xfmr_table = {}
    mode = None
    for row in lm:
        if not row:
            continue
        head = _strip(row[0])
        if head.startswith("Pole CU Average Hours"):
            mode = "pole"
            continue
        if head.startswith("Transformer CU Average Hours"):
            mode = "xfmr"
            continue
        if head in ("Crossarm CU Average Hours", "Bracket CU Average Hours"):
            mode = None
            continue
        if mode == "pole" and head in ("Small", "Medium", "Large"):
            pole_table[head] = {"height_range": _strip(row[1]),
                                 "install_hours": row[2], "remove_hours": row[3]}
        if mode == "xfmr" and isinstance(row[0], (int, float)) and len(row) >= 4:
            xfmr_table[int(row[0])] = {"cu_count": row[1],
                                        "install_hours": row[2], "remove_hours": row[3]}
    out["tables"]["pole_install_remove_hours_by_size"] = pole_table
    out["tables"]["transformer_install_remove_hours_by_kVA"] = xfmr_table

    out["units"] = {
        "INSTALL_HOURS": "direct crew-hours to install one construction unit (CU)",
        "REMOVE_HOURS": "direct crew-hours to remove one CU",
        "effective_hours": "direct_hours * ILM  (ILM already includes travel/setup/safety)",
    }
    out["caveats"] = [
        "Apply the ILM once to summed DIRECT hours. Do NOT separately add travel/setup/safety — "
        "the ILM already accounts for them (avoids double counting).",
        "'Labor only work' adders are DIRECT-hour adders (e.g. Restricted Access 0.5 h) and are added "
        "to direct hours BEFORE applying the ILM.",
        "Values are averages across construction units; individual jobs vary. Treat as planning estimates.",
        "Excavation adders are per cubic foot and require a volume not present in the storm data.",
    ]
    return out


def main() -> None:
    if not (EXTRACT / "Data1" / "Customer_Clip.dbf").exists():
        raise SystemExit("data/extracted/ is empty — run `python -m scripts.extract_data` first.")
    report = inspect()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED / "inspection_report.json"
    out_path.write_text(json.dumps(report, indent=2))

    # Human-readable summary (aggregates only; no PII)
    r = report["relationships"]
    print("=" * 70)
    print("Beacon data inspection — verified relationships (no PII printed)")
    print("=" * 70)
    pj = r["premise_join"]
    print(f"Customers: {pj['customers_total']:,} | matched_upstream rows: {pj['matched_upstream_rows']:,}")
    print(f"Premise join (Customer.premise_nu -> matched_upstream): "
          f"{pj['customer_join_rate_pct']}% ({pj['customers_joined_to_topology']:,} joined, "
          f"{pj['customers_missing_topology']} unmapped)")
    ct = r["customer_transformer_key"]
    print(f"Customer->transformer key agreement (aep_xfmr_l): "
          f"{ct['agreement_rate_pct']}% ({ct['disagree']} disagree)")
    ei = r["equipment_identifiers"]
    print(f"Equipment ids: transformer {ei['mu_transformer_in_layer_pct']}% matched, "
          f"isolating {ei['mu_isolating_in_any_layer_pct']}% matched")
    uo = r["upstream_ordering"]
    print(f"Upstream chain: mean {uo['isolating_devices_per_premise_mean']} isolating devices/premise "
          f"(max {uo['isolating_devices_per_premise_max']})")
    dc = r["damage_to_circuit"]
    print(f"Damage->circuit (anonymized name): {dc['match_rate_pct']}% "
          f"({dc['damage_rows']} damage rows, {dc['distinct_damage_circuits']} circuits)")
    print(f"  Damage nature: {dc['evidence_nature']}")
    lab = report["labor"]
    print(f"Labor ILM: {lab['indirect_labor_multiplier']['value']} "
          f"(covers {lab['indirect_labor_multiplier']['covers']})")
    print("-" * 70)
    print(f"Full report written to {out_path.relative_to(REPO_ROOT)}")
    print(f"Unresolved questions for AEP mentors: {len(report['unresolved'])} (see report)")


if __name__ == "__main__":
    main()
