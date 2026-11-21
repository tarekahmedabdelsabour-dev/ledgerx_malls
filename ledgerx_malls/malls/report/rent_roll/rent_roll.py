import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from ledgerx_malls import data
from ledgerx_malls.engine.billing import month_start, monthly_charge
from ledgerx_malls.engine.stats import wale_years


def execute(filters=None):
	filters = frappe._dict(filters or {})
	today = getdate(nowdate())
	f = {"docstatus": 1}
	if filters.mall:
		f["mall"] = filters.mall
	if not filters.include_ended:
		f["lease_status"] = ["in", ["Active", "Upcoming"]]
	rows, wale_in, total_rent, total_area = [], [], 0.0, 0.0
	for name in frappe.get_all("Mall Lease", filters=f, pluck="name", order_by="mall, start_date"):
		l = frappe.get_doc("Mall Lease", name)
		t = data.lease_terms(l)
		m = month_start(today)
		rent_now = monthly_charge(t["base"], t["esc"], t["start"], t["end"], m, [], "Rent") if t["model"] != "Percentage of Sales" else 0.0
		svc_now = monthly_charge(t["service"], t["service_esc"], t["start"], t["end"], m, [], "Service Charge") if t["service"] else 0.0
		area = flt(l.total_area)
		rows.append({"lease": l.name, "mall": l.mall, "units": ", ".join(u.unit.split("-", 1)[-1] for u in l.units), "tenant": l.tenant, "trade_name": l.trade_name, "area": area, "start": l.start_date,
			"end": t["end"], "status": l.lease_status, "model": l.rent_model, "turnover_pct": flt(l.turnover_pct), "rent": rent_now, "rent_sqm": round(rent_now / area, 2) if area else 0, "service": svc_now,
			"deposit": flt(l.security_deposit)})
		if l.lease_status == "Active":
			wale_in.append((t["end"], rent_now or area))
			total_rent += rent_now
			total_area += area
	cols = [
		{"label": _("Lease"), "fieldname": "lease", "fieldtype": "Link", "options": "Mall Lease", "width": 120},
		{"label": _("Mall"), "fieldname": "mall", "fieldtype": "Link", "options": "Mall", "width": 110},
		{"label": _("Units"), "fieldname": "units", "fieldtype": "Data", "width": 90},
		{"label": _("Brand"), "fieldname": "trade_name", "fieldtype": "Data", "width": 150},
		{"label": _("Area (sqm)"), "fieldname": "area", "fieldtype": "Float", "width": 90},
		{"label": _("Start"), "fieldname": "start", "fieldtype": "Date", "width": 95},
		{"label": _("End"), "fieldname": "end", "fieldtype": "Date", "width": 95},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 85},
		{"label": _("Rent Model"), "fieldname": "model", "fieldtype": "Data", "width": 170},
		{"label": _("% of Sales"), "fieldname": "turnover_pct", "fieldtype": "Percent", "width": 80},
		{"label": _("Rent This Month"), "fieldname": "rent", "fieldtype": "Currency", "width": 120},
		{"label": _("Rent per sqm"), "fieldname": "rent_sqm", "fieldtype": "Currency", "width": 100},
		{"label": _("Service Charge"), "fieldname": "service", "fieldtype": "Currency", "width": 110},
		{"label": _("Security Deposit"), "fieldname": "deposit", "fieldtype": "Currency", "width": 110},
	]
	msg = _("Active leases: monthly fixed rent {0} over {1} sqm. Weighted average lease expiry: {2} years.").format(frappe.format_value(total_rent, {"fieldtype": "Currency"}), flt(total_area, 1), wale_years(wale_in, today))
	return cols, rows, msg
