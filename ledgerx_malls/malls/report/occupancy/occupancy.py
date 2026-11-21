import frappe
from frappe import _
from frappe.utils import flt

from ledgerx_malls.engine.stats import occupancy_pct


def execute(filters=None):
	filters = frappe._dict(filters or {})
	f = {"active": 1}
	if filters.mall:
		f["mall"] = filters.mall
	units = frappe.get_all("Mall Unit", filters=f, fields=["name", "unit_no", "mall", "floor", "category", "area_sqm", "status", "current_tenant", "list_rent_sqm"], order_by="mall, floor, unit_no")
	by = {}
	for u in units:
		key = (u.mall, u.floor or "-") if filters.group_by == "Floor" else (u.mall, u.category or "-") if filters.group_by == "Category" else (u.mall, "-")
		d = by.setdefault(key, {"mall": key[0], "group": key[1] if key[1] != "-" else "", "units": 0, "vacant_units": 0, "area": 0.0, "occupied": 0.0, "vacant_area": 0.0, "lost_rent": 0.0})
		d["units"] += 1
		d["area"] += flt(u.area_sqm)
		if u.status in ("Occupied", "Fit-out"):
			d["occupied"] += flt(u.area_sqm)
		elif u.status in ("Vacant", "Reserved"):
			d["vacant_units"] += 1
			d["vacant_area"] += flt(u.area_sqm)
			d["lost_rent"] += flt(u.area_sqm) * flt(u.list_rent_sqm)
	rows = []
	for d in by.values():
		d["occupancy"] = occupancy_pct(d["occupied"], d["area"])
		rows.append(d)
	cols = [
		{"label": _("Mall"), "fieldname": "mall", "fieldtype": "Link", "options": "Mall", "width": 130},
		{"label": filters.group_by or _("Group"), "fieldname": "group", "fieldtype": "Data", "width": 150},
		{"label": _("Units"), "fieldname": "units", "fieldtype": "Int", "width": 70},
		{"label": _("Vacant or Reserved Units"), "fieldname": "vacant_units", "fieldtype": "Int", "width": 90},
		{"label": _("Area (sqm)"), "fieldname": "area", "fieldtype": "Float", "width": 100},
		{"label": _("Occupied (sqm)"), "fieldname": "occupied", "fieldtype": "Float", "width": 110},
		{"label": _("Vacant (sqm)"), "fieldname": "vacant_area", "fieldtype": "Float", "width": 100},
		{"label": _("Occupancy %"), "fieldname": "occupancy", "fieldtype": "Percent", "width": 100},
		{"label": _("Rent Lost per Month at Asking Price"), "fieldname": "lost_rent", "fieldtype": "Currency", "width": 170},
	]
	chart = {"data": {"labels": [f"{r['mall']} {r['group']}".strip() for r in rows], "datasets": [{"name": _("Occupancy %"), "values": [r["occupancy"] for r in rows]}]}, "type": "bar"}
	return cols, rows, None, chart
