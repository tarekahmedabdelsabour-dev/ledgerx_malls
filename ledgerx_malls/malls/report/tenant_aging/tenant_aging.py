import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from ledgerx_malls.engine.stats import bucket_of


def execute(filters=None):
	filters = frappe._dict(filters or {})
	today = getdate(filters.as_of or nowdate())
	cond, vals = "", {}
	if filters.mall:
		cond = " and si.ml_mall = %(mall)s"
		vals["mall"] = filters.mall
	rows = frappe.db.sql(
		f"""select si.customer, si.ml_lease lease, si.ml_mall mall, si.name, si.due_date, si.outstanding_amount o from `tabSales Invoice` si
		where si.docstatus = 1 and si.outstanding_amount > 0.005 and ifnull(si.ml_mall, '') != '' {cond}""", vals, as_dict=True)
	by = {}
	for r in rows:
		d = by.setdefault(r.lease, {"lease": r.lease, "mall": r.mall, "customer": r.customer, "not_due": 0.0, "b1": 0.0, "b2": 0.0, "b3": 0.0, "b4": 0.0, "total": 0.0, "oldest": 0})
		days = (today - getdate(r.due_date)).days
		b = bucket_of(days)
		key = {"Not Due": "not_due", "1-30": "b1", "31-60": "b2", "61-90": "b3", "Over 90": "b4"}[b]
		d[key] += flt(r.o)
		d["total"] += flt(r.o)
		d["oldest"] = max(d["oldest"], days)
	names = {r.name: r.trade_name for r in frappe.get_all("Mall Lease", filters={"name": ["in", list(by)]}, fields=["name", "trade_name"])} if by else {}
	out = sorted(by.values(), key=lambda x: -x["total"])
	for d in out:
		d["trade_name"] = names.get(d["lease"])
		d["oldest"] = max(d["oldest"], 0)
	cols = [
		{"label": _("Lease"), "fieldname": "lease", "fieldtype": "Link", "options": "Mall Lease", "width": 120},
		{"label": _("Brand"), "fieldname": "trade_name", "fieldtype": "Data", "width": 160},
		{"label": _("Mall"), "fieldname": "mall", "fieldtype": "Link", "options": "Mall", "width": 110},
		{"label": _("Not Due"), "fieldname": "not_due", "fieldtype": "Currency", "width": 105},
		{"label": _("1 - 30 days"), "fieldname": "b1", "fieldtype": "Currency", "width": 105},
		{"label": _("31 - 60 days"), "fieldname": "b2", "fieldtype": "Currency", "width": 105},
		{"label": _("61 - 90 days"), "fieldname": "b3", "fieldtype": "Currency", "width": 105},
		{"label": _("Over 90 days"), "fieldname": "b4", "fieldtype": "Currency", "width": 105},
		{"label": _("Total Owed"), "fieldname": "total", "fieldtype": "Currency", "width": 115},
		{"label": _("Oldest (days overdue)"), "fieldname": "oldest", "fieldtype": "Int", "width": 120},
	]
	return cols, out
