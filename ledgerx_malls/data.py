"""Readers and small writers shared by the mall documents, tasks and reports."""
import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, nowdate

from .engine.billing import month_end, month_start
from .engine.stats import overlaps


def settings():
	return frappe.get_cached_doc("Mall Settings")


def effective_end(end_date, terminated_on=None):
	e = getdate(end_date)
	if terminated_on:
		t = getdate(terminated_on)
		if t < e:
			return t
	return e


def lease_terms(doc):
	"""Everything the billing engine needs from a lease document."""
	return {
		"start": getdate(doc.start_date), "end": effective_end(doc.end_date, doc.get("terminated_on")), "model": doc.rent_model, "base": flt(doc.base_rent), "esc": flt(doc.rent_escalation_pct),
		"turnover_pct": flt(doc.turnover_pct), "service": flt(doc.service_per_sqm) * flt(doc.total_area), "service_esc": flt(doc.service_escalation_pct), "marketing_pct": flt(doc.marketing_pct),
		"free": [{"from": getdate(f.from_date), "to": getdate(f.to_date), "applies": f.applies_to or "All"} for f in doc.get("free_periods") or []],
	}


def leases_in_force(mall, first, last, names=None):
	"""Submitted leases of a mall with at least one day inside [first, last]."""
	rows = frappe.get_all("Mall Lease", filters={"docstatus": 1, "mall": mall, "start_date": ["<=", last], "end_date": [">=", first]}, pluck="name")
	out = []
	for n in rows:
		d = frappe.get_doc("Mall Lease", n)
		if getdate(d.start_date) <= last and effective_end(d.end_date, d.terminated_on) >= first and (not names or n in names):
			out.append(d)
	return out


def lease_status_of(doc, today=None):
	today = getdate(today or nowdate())
	if doc.docstatus == 2:
		return "Terminated"
	if doc.get("terminated_on") and getdate(doc.terminated_on) < today:
		return "Terminated"
	if today < getdate(doc.start_date):
		return "Upcoming"
	if today > getdate(doc.end_date):
		return "Expired"
	return "Active"


def conflicting_lease(unit, start, end, exclude=None):
	"""Name of another submitted lease holding this unit during the given dates."""
	rows = frappe.db.sql(
		"""select l.name, l.start_date, l.end_date, l.terminated_on from `tabMall Lease` l join `tabLease Unit` u on u.parent = l.name
		where l.docstatus = 1 and u.unit = %s and l.name != %s""", (unit, exclude or ""), as_dict=True)
	for r in rows:
		e = effective_end(r.end_date, r.terminated_on)
		if overlaps(getdate(start), getdate(end) if end else None, getdate(r.start_date), e):
			return r.name
	return None


def sync_unit(unit):
	"""Brings a unit's status, current lease and tenant in line with the leases. A unit set to Maintenance stays so while no lease is in force."""
	today = getdate(nowdate())
	rows = frappe.db.sql(
		"""select l.name, l.tenant, l.start_date, l.end_date, l.terminated_on from `tabMall Lease` l join `tabLease Unit` u on u.parent = l.name
		where l.docstatus = 1 and u.unit = %s order by l.start_date""", unit, as_dict=True)
	current = upcoming = None
	for r in rows:
		s, e = getdate(r.start_date), effective_end(r.end_date, r.terminated_on)
		if s <= today <= e:
			current = r
		elif s > today and upcoming is None:
			upcoming = r
	cur_status = frappe.db.get_value("Mall Unit", unit, "status")
	if current:
		lease_free_all = frappe.db.sql("select 1 from `tabLease Free Period` where parent = %s and applies_to = 'All' and %s between from_date and to_date", (current.name, today))
		status, lease, tenant = ("Fit-out" if lease_free_all else "Occupied"), current.name, current.tenant
	elif upcoming:
		status, lease, tenant = ("Maintenance" if cur_status == "Maintenance" else "Reserved"), None, upcoming.tenant
	else:
		status, lease, tenant = ("Maintenance" if cur_status == "Maintenance" else ("Reserved" if cur_status == "Reserved" else "Vacant")), None, None
		if cur_status == "Occupied" or cur_status == "Fit-out":
			status = "Vacant"
	frappe.db.set_value("Mall Unit", unit, {"status": status, "current_lease": lease, "current_tenant": tenant}, update_modified=False)


def update_mall_totals(mall):
	rows = frappe.get_all("Mall Unit", filters={"mall": mall, "active": 1}, fields=["area_sqm", "status"])
	total = sum(flt(r.area_sqm) for r in rows)
	occ = sum(flt(r.area_sqm) for r in rows if r.status in ("Occupied", "Fit-out"))
	frappe.db.set_value("Mall", mall, {"total_gla": total, "occupied_area": occ, "occupancy_pct": round(occ / total * 100, 2) if total else 0}, update_modified=False)


def refresh_all():
	for name in frappe.get_all("Mall Lease", filters={"docstatus": 1}, pluck="name"):
		d = frappe.get_doc("Mall Lease", name)
		st = lease_status_of(d)
		if st != d.lease_status:
			d.db_set("lease_status", st, update_modified=False)
	for u in frappe.get_all("Mall Unit", pluck="name"):
		sync_unit(u)
	for m in frappe.get_all("Mall", pluck="name"):
		update_mall_totals(m)


def manager_users(mall):
	u = frappe.db.get_value("Mall", mall, "manager_user")
	users = [u] if u else [r.parent for r in frappe.get_all("Has Role", filters={"role": "Mall Manager", "parenttype": "User"}, fields=["parent"])]
	return [x for x in set(users) if x and frappe.db.get_value("User", x, "enabled")]
