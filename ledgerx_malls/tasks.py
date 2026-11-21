import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, getdate, nowdate

from . import data
from .engine.billing import month_end


def daily():
	for fn in (_refresh, _expiry_alerts, _sales_reminders):
		try:
			fn()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title=f"ledgerx_malls daily task failed: {fn.__name__}")


def _refresh():
	data.refresh_all()


def _todo(user, text, ref_type, ref_name):
	if frappe.db.exists("ToDo", {"reference_type": ref_type, "reference_name": ref_name, "allocated_to": user, "status": "Open", "description": text}):
		return
	frappe.get_doc({"doctype": "ToDo", "allocated_to": user, "description": text, "reference_type": ref_type, "reference_name": ref_name, "date": nowdate()}).insert(ignore_permissions=True)


def _expiry_alerts():
	days = cint(data.settings().expiry_alert_days) or 180
	limit = add_days(nowdate(), days)
	for l in frappe.get_all("Mall Lease", filters={"docstatus": 1, "lease_status": "Active", "end_date": ["between", [nowdate(), limit]], "terminated_on": ["is", "not set"]}, fields=["name", "mall", "trade_name", "end_date"]):
		for u in data.manager_users(l.mall):
			_todo(u, _("Lease {0} ({1}) ends on {2}: renew or plan the next tenant.").format(l.name, l.trade_name, l.end_date), "Mall Lease", l.name)


def _sales_reminders():
	"""From the 5th of the month: one reminder per mall listing how many tenants have not yet reported last month's sales."""
	today = getdate(nowdate())
	if today.day < 5:
		return
	prev = add_months(today.replace(day=1), -1)
	for m in frappe.get_all("Mall", filters={"active": 1}, pluck="name"):
		leases = frappe.get_all("Mall Lease", filters={"docstatus": 1, "mall": m, "lease_status": "Active", "rent_model": ["!=", "Fixed"]}, pluck="name")
		missing = [l for l in leases if not frappe.db.exists("Tenant Sales", {"lease": l, "month": ["between", [prev, month_end(prev)]]})]
		if missing:
			for u in data.manager_users(m):
				_todo(u, _("{0}: {1} tenants on turnover rent have not reported sales for {2}.").format(m, len(missing), prev.strftime("%B %Y")), "Mall", m)
