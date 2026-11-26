import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, getdate, nowdate

from ledgerx_malls import data
from ledgerx_malls.engine.billing import base_rent_applies


class MallLease(Document):
	def validate(self):
		if getdate(self.end_date) <= getdate(self.start_date):
			frappe.throw(_("The lease must end after it starts"))
		tenant = frappe.db.get_value("Mall Tenant", self.tenant, ["status", "customer"], as_dict=1)
		if tenant.status == "Former":
			frappe.throw(_("Tenant {0} is marked Former").format(self.tenant))
		if not tenant.customer:
			frappe.throw(_("Tenant {0} has no customer account").format(self.tenant))
		if not self.units:
			frappe.throw(_("Add at least one unit"))
		seen, total = set(), 0.0
		for u in self.units:
			if u.unit in seen:
				frappe.throw(_("Unit {0} is listed twice").format(u.unit))
			seen.add(u.unit)
			info = frappe.db.get_value("Mall Unit", u.unit, ["mall", "area_sqm", "active"], as_dict=1)
			if info.mall != self.mall:
				frappe.throw(_("Unit {0} belongs to another mall").format(u.unit))
			if not info.active:
				frappe.throw(_("Unit {0} is not active").format(u.unit))
			u.area_sqm = info.area_sqm
			total += flt(info.area_sqm)
			clash = data.conflicting_lease(u.unit, self.start_date, self.end_date, self.name)
			if clash:
				frappe.throw(_("Unit {0} is already leased in these dates by {1}").format(u.unit, clash))
		self.total_area = total
		if self.rent_model != "Fixed" and flt(self.turnover_pct) <= 0:
			frappe.throw(_("Enter the percentage of sales"))
		if self.rent_model == "Percentage of Sales":
			self.base_rent = 0
		else:
			if flt(self.rent_amount) <= 0:
				frappe.throw(_("Enter the rent amount"))
			self.base_rent = round(flt(self.rent_amount) * (total if self.rent_basis == "Per sqm per Month" else 1), 2)
		for f in self.free_periods:
			if getdate(f.to_date) < getdate(f.from_date):
				frappe.throw(_("Rent-free row {0}: the end is before the start").format(f.idx))
			if getdate(f.from_date) < getdate(self.start_date) or getdate(f.to_date) > getdate(self.end_date):
				frappe.throw(_("Rent-free row {0} falls outside the lease dates").format(f.idx))
		for fld in ("rent_escalation_pct", "service_escalation_pct", "marketing_pct", "turnover_pct"):
			if not 0 <= flt(self.get(fld)) <= 100:
				frappe.throw(_("{0} must be between 0 and 100").format(self.meta.get_label(fld)))
		if flt(self.security_deposit) < 0 or flt(self.service_per_sqm) < 0:
			frappe.throw(_("Amounts cannot be negative"))
		self.lease_status = data.lease_status_of(self)

	def on_submit(self):
		self._sync()

	def on_cancel(self):
		self.db_set("lease_status", "Terminated", update_modified=False)
		self._sync()

	def _sync(self):
		for u in self.units:
			data.sync_unit(u.unit)
		data.update_mall_totals(self.mall)

	@frappe.whitelist(methods=["POST"])
	def terminate(self, date, reason=None):
		"""Ends the lease on a given date. Billing stops after that day; the units are released once the date has passed."""
		self.check_permission("write")
		self.check_permission("submit")
		if self.docstatus != 1:
			frappe.throw(_("Only a submitted lease can be terminated"))
		d = getdate(date)
		if d < getdate(self.start_date) or d > getdate(self.end_date):
			frappe.throw(_("The termination date must fall inside the lease"))
		self.db_set({"terminated_on": d, "termination_reason": reason or ""})
		self.db_set("lease_status", data.lease_status_of(self), update_modified=False)
		self._sync()
		return self.lease_status

	@frappe.whitelist(methods=["POST"])
	def renew(self, years=1, rent_increase_pct=0):
		"""A draft renewal starting the day after this lease ends, with the same terms and a new rent."""
		self.check_permission("write")
		self.check_permission("create")
		new = frappe.copy_doc(self)
		new.renewed_from = self.name
		new.start_date = add_days(getdate(self.end_date), 1)
		new.end_date = add_days(frappe.utils.add_years(new.start_date, int(years)), -1)
		new.terminated_on = None
		new.termination_reason = None
		new.lease_status = "Upcoming"
		new.free_periods = []
		new.deposit_status = "Pending"
		inc = 1 + flt(rent_increase_pct) / 100.0
		new.rent_amount = round(flt(self.rent_amount) * inc, 2)
		new.service_per_sqm = round(flt(self.service_per_sqm) * inc, 2)
		new.insert()
		return new.name
