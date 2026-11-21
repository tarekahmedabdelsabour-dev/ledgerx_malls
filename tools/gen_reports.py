"""Writes the report JSON files. Run from the repo root. The .py/.js of each report are hand written and never overwritten."""
import json
import os

BASE = os.path.join(os.path.dirname(__file__), "..", "ledgerx_malls", "malls", "report")
TS = "2026-11-21 08:00:00.000000"
ROLES = ["Mall Manager", "Leasing Officer", "Mall Accountant", "Mall Operations", "Accounts Manager"]
REPORTS = [("Rent Roll", "Mall Lease"), ("Occupancy", "Mall Unit"), ("Tenant Aging", "Mall Tenant"), ("Tenant Sales Performance", "Tenant Sales"),
	("Lease Expiry", "Mall Lease"), ("Footfall and Sales", "Footfall"), ("Billing and Collection", "Mall Billing Run")]
for name, ref in REPORTS:
	slug = name.lower().replace(" ", "_")
	folder = os.path.join(BASE, slug)
	os.makedirs(folder, exist_ok=True)
	open(os.path.join(folder, "__init__.py"), "a").close()
	roles = ROLES + (["Accounts User"] if name in ("Tenant Aging", "Billing and Collection") else [])
	with open(os.path.join(folder, slug + ".json"), "w") as fh:
		json.dump({"add_total_row": 0, "columns": [], "creation": TS, "disabled": 0, "docstatus": 0, "doctype": "Report", "filters": [], "idx": 0, "is_standard": "Yes",
			"modified": TS, "modified_by": "Administrator", "module": "Malls", "name": name, "owner": "Administrator", "prepared_report": 0, "ref_doctype": ref,
			"report_name": name, "report_type": "Script Report", "roles": [{"role": r} for r in roles]}, fh, indent=1)
		fh.write("\n")
print(len(REPORTS), "reports")
