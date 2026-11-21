import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, nowdate

from ledgerx_malls import data


def execute(filters=None):
	filters = frappe._dict(filters or {})
	days = int(filters.within_days or 365)
	today = getdate(nowdate())
	limit = add_days(today, days)
	f = {"docstatus": 1, "lease_status": "Active", "end_date": ["between", [today, limit]]}
	if filters.mall:
		f["mall"] = filters.mall
	out = []
	for l in frappe.get_all("Mall Lease", filters=f, fields=["name", "mall", "trade_name", "tenant", "end_date", "total_area", "base_rent", "rent_model", "terminated_on", "renewed_from"], order_by="end_date"):
		renewed = frappe.db.exists("Mall Lease", {"renewed_from": l.name, "docstatus": ["<", 2]})
		out.append({"lease": l.name, "mall": l.mall, "trade_name": l.trade_name, "end_date": l.end_date, "days_left": (getdate(l.end_date) - today).days, "area": flt(l.total_area),
			"rent": flt(l.base_rent), "model": l.rent_model, "renewal": renewed or "", "action": _("Renewal drafted") if renewed else _("Decide: renew or re-let")})
	cols = [
		{"label": _("Lease"), "fieldname": "lease", "fieldtype": "Link", "options": "Mall Lease", "width": 120},
		{"label": _("Mall"), "fieldname": "mall", "fieldtype": "Link", "options": "Mall", "width": 110},
		{"label": _("Brand"), "fieldname": "trade_name", "fieldtype": "Data", "width": 160},
		{"label": _("Ends"), "fieldname": "end_date", "fieldtype": "Date", "width": 100},
		{"label": _("Days Left"), "fieldname": "days_left", "fieldtype": "Int", "width": 80},
		{"label": _("Area (sqm)"), "fieldname": "area", "fieldtype": "Float", "width": 90},
		{"label": _("Base Rent per Month"), "fieldname": "rent", "fieldtype": "Currency", "width": 130},
		{"label": _("Rent Model"), "fieldname": "model", "fieldtype": "Data", "width": 170},
		{"label": _("Renewal"), "fieldname": "renewal", "fieldtype": "Link", "options": "Mall Lease", "width": 120},
		{"label": _("Action"), "fieldname": "action", "fieldtype": "Data", "width": 180},
	]
	return cols, out
