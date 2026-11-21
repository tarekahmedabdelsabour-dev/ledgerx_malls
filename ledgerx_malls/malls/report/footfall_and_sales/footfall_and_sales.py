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
		cond = " and mall = %(mall)s"
		vals["mall"] = filters.mall
	foot = {(r.mall, r.m): int(r.v) for r in frappe.db.sql(f"select mall, date_format(date, '%%Y-%%m-01') m, sum(visitors) v from `tabFootfall` where date between %(a)s and %(b)s {cond} group by mall, m", vals, as_dict=True)}
	sales = {(r.mall, r.m): (flt(r.s), r.n) for r in frappe.db.sql(f"select mall, date_format(month, '%%Y-%%m-01') m, sum(net_sales) s, count(*) n from `tabTenant Sales` where month between %(a)s and %(b)s {cond} group by mall, m", vals, as_dict=True)}
	area = {r.name: flt(r.total_gla) for r in frappe.get_all("Mall", fields=["name", "total_gla"])}
	out = []
	for key in sorted(set(foot) | set(sales)):
		v = foot.get(key, 0)
		s, n = sales.get(key, (0.0, 0))
		out.append({"mall": key[0], "month": key[1], "visitors": v, "sales": s, "tenants_reporting": n, "sales_per_visitor": round(s / v, 2) if v else None, "sales_sqm": round(s / area[key[0]], 2) if area.get(key[0]) else None})
	cols = [
		{"label": _("Mall"), "fieldname": "mall", "fieldtype": "Link", "options": "Mall", "width": 130},
		{"label": _("Month"), "fieldname": "month", "fieldtype": "Date", "width": 100},
		{"label": _("Visitors"), "fieldname": "visitors", "fieldtype": "Int", "width": 100},
		{"label": _("Tenants Reporting Sales"), "fieldname": "tenants_reporting", "fieldtype": "Int", "width": 130},
		{"label": _("Reported Net Sales"), "fieldname": "sales", "fieldtype": "Currency", "width": 140},
		{"label": _("Sales per Visitor"), "fieldname": "sales_per_visitor", "fieldtype": "Currency", "width": 120},
		{"label": _("Sales per sqm of Mall"), "fieldname": "sales_sqm", "fieldtype": "Currency", "width": 140},
	]
	chart = {"data": {"labels": [str(r["month"]) for r in out], "datasets": [{"name": _("Visitors"), "values": [r["visitors"] for r in out]}]}, "type": "line"}
	return cols, out, None, chart
