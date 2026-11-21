import frappe
from frappe import _
from frappe.utils import flt, getdate

from ledgerx_malls.engine.billing import month_end, month_start


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not (filters.from_month and filters.to_month):
		frappe.throw(_("Choose the months"))
	first, last = month_start(getdate(filters.from_month)), month_end(getdate(filters.to_month))
	cond, vals = "", {"a": first, "b": last}
	if filters.mall:
		cond = " and ml_mall = %(mall)s"
		vals["mall"] = filters.mall
	rows = frappe.db.sql(
		f"""select ml_mall mall, ml_period m, count(*) invoices, sum(grand_total) billed, sum(grand_total - outstanding_amount) collected, sum(outstanding_amount) open
		from `tabSales Invoice` where docstatus = 1 and ifnull(ml_mall, '') != '' and ml_period between %(a)s and %(b)s {cond} group by ml_mall, ml_period order by ml_period""", vals, as_dict=True)
	out = [{"mall": r.mall, "month": r.m, "invoices": r.invoices, "billed": flt(r.billed), "collected": flt(r.collected), "open": flt(r.open), "rate": round(flt(r.collected) / flt(r.billed) * 100, 1) if r.billed else 0} for r in rows]
	cols = [
		{"label": _("Mall"), "fieldname": "mall", "fieldtype": "Link", "options": "Mall", "width": 130},
		{"label": _("Billing Month"), "fieldname": "month", "fieldtype": "Date", "width": 110},
		{"label": _("Invoices"), "fieldname": "invoices", "fieldtype": "Int", "width": 80},
		{"label": _("Billed"), "fieldname": "billed", "fieldtype": "Currency", "width": 130},
		{"label": _("Collected"), "fieldname": "collected", "fieldtype": "Currency", "width": 130},
		{"label": _("Still Open"), "fieldname": "open", "fieldtype": "Currency", "width": 130},
		{"label": _("Collection %"), "fieldname": "rate", "fieldtype": "Percent", "width": 100},
	]
	chart = {"data": {"labels": [str(r["month"]) for r in out], "datasets": [{"name": _("Billed"), "values": [r["billed"] for r in out]}, {"name": _("Collected"), "values": [r["collected"] for r in out]}]}, "type": "bar"}
	return cols, out, None, chart
