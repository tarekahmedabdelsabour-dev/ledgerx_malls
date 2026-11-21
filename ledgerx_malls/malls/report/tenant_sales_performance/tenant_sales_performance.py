import frappe
from frappe import _
from frappe.utils import flt

from ledgerx_malls import data
from ledgerx_malls.engine.billing import add_months, month_end, month_start, monthly_charge
from ledgerx_malls.engine.stats import occupancy_cost_ratio, sales_per_sqm


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not (filters.from_month and filters.to_month):
		frappe.throw(_("Choose the months"))
	first, last = month_start(frappe.utils.getdate(filters.from_month)), month_end(frappe.utils.getdate(filters.to_month))
	cond, vals = "", {"a": first, "b": last}
	if filters.mall:
		cond += " and ts.mall = %(mall)s"
		vals["mall"] = filters.mall
	rows = frappe.db.sql(
		f"""select ts.lease, sum(ts.net_sales) net, count(*) months, sum(ts.status = 'Verified') verified from `tabTenant Sales` ts
		where ts.month between %(a)s and %(b)s {cond} group by ts.lease""", vals, as_dict=True)
	out = []
	for r in rows:
		l = frappe.get_doc("Mall Lease", r.lease)
		if filters.category and frappe.db.get_value("Mall Tenant", l.tenant, "category") != filters.category:
			continue
		t = data.lease_terms(l)
		# what the tenant was charged for the same months: rent + service charge at the lease terms
		rent = svc = 0.0
		m = first
		while m <= last:
			rent += monthly_charge(t["base"], t["esc"], t["start"], t["end"], m, t["free"], "Rent") if t["model"] != "Percentage of Sales" else 0.0
			svc += monthly_charge(t["service"], t["service_esc"], t["start"], t["end"], m, t["free"], "Service Charge") if t["service"] else 0.0
			m = add_months(m, 1)
		area = flt(l.total_area)
		net = flt(r.net)
		out.append({"lease": l.name, "mall": l.mall, "trade_name": l.trade_name, "category": frappe.db.get_value("Mall Tenant", l.tenant, "category"), "area": area, "net_sales": net,
			"sales_sqm_month": round(sales_per_sqm(net, area) / max(r.months, 1), 2), "rent": round(rent, 2), "service": round(svc, 2), "ratio": occupancy_cost_ratio(rent, svc, net),
			"months": r.months, "verified": "yes" if r.verified == r.months else "no"})
	out.sort(key=lambda x: -x["sales_sqm_month"])
	cols = [
		{"label": _("Lease"), "fieldname": "lease", "fieldtype": "Link", "options": "Mall Lease", "width": 115},
		{"label": _("Brand"), "fieldname": "trade_name", "fieldtype": "Data", "width": 150},
		{"label": _("Category"), "fieldname": "category", "fieldtype": "Link", "options": "Mall Category", "width": 130},
		{"label": _("Area (sqm)"), "fieldname": "area", "fieldtype": "Float", "width": 85},
		{"label": _("Months Reported"), "fieldname": "months", "fieldtype": "Int", "width": 90},
		{"label": _("Net Sales"), "fieldname": "net_sales", "fieldtype": "Currency", "width": 120},
		{"label": _("Sales per sqm per Month"), "fieldname": "sales_sqm_month", "fieldtype": "Currency", "width": 130},
		{"label": _("Rent"), "fieldname": "rent", "fieldtype": "Currency", "width": 110},
		{"label": _("Service Charge"), "fieldname": "service", "fieldtype": "Currency", "width": 110},
		{"label": _("Occupancy Cost % of Sales"), "fieldname": "ratio", "fieldtype": "Percent", "width": 140},
		{"label": _("All Verified"), "fieldname": "verified", "fieldtype": "Data", "width": 85},
	]
	return cols, out, _("A tenant whose occupancy cost is above about 15% of sales is usually under strain; far below 8% may mean the rent is too low.")
