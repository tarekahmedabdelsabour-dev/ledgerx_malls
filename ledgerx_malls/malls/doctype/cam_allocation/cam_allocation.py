import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from ledgerx_malls import data
from ledgerx_malls.engine.cam import cam_shares


class CAMAllocation(Document):
	def validate(self):
		if getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("The period ends before it starts"))
		if flt(self.total_expense) < 0:
			frappe.throw(_("Expenses cannot be negative"))

	@frappe.whitelist(methods=["POST"])
	def load_expenses(self):
		"""Sum of the expense postings of the mall's cost center in the period."""
		self.check_permission("write")
		cc = frappe.db.get_value("Mall", self.mall, "cost_center")
		if not cc:
			frappe.throw(_("Set a cost center on the mall first"))
		company = frappe.db.get_value("Mall", self.mall, "company")
		r = frappe.db.sql(
			"""select sum(g.debit - g.credit) from `tabGL Entry` g join `tabAccount` a on a.name = g.account
			where g.is_cancelled = 0 and g.company = %s and g.cost_center = %s and a.root_type = 'Expense' and g.posting_date between %s and %s
			and g.voucher_type not in ('Period Closing Voucher')""", (company, cc, self.from_date, self.to_date))[0][0]
		self.total_expense = round(flt(r), 2)
		self.save()
		return self.total_expense

	@frappe.whitelist(methods=["POST"])
	def allocate(self):
		"""Splits the expenses by leased area x days in force, so a tenant who stayed half the period pays half the share."""
		self.check_permission("write")
		if self.status == "Billed":
			frappe.throw(_("This allocation was already billed"))
		if flt(self.total_expense) <= 0:
			frappe.throw(_("Enter the expenses to recover first"))
		first, last = getdate(self.from_date), getdate(self.to_date)
		days = (last - first).days + 1
		leases = [l for l in data.leases_in_force(self.mall, first, last) if l.recover_cam]
		weights, rows = [], []
		for l in leases:
			s, e = max(getdate(l.start_date), first), min(data.effective_end(l.end_date, l.terminated_on), last)
			d = (e - s).days + 1
			weights.append(flt(l.total_area) * d)
			rows.append(l)
		total_gla = flt(frappe.db.get_value("Mall", self.mall, "total_gla"))
		vacant = max(total_gla * days - sum(weights), 0.0)
		parts, landlord = cam_shares(flt(self.total_expense), weights, vacant, bool(self.landlord_bears_vacant))
		self.lines = []
		for l, w, amt in zip(rows, weights, parts):
			self.append("lines", {"lease": l.name, "trade_name": l.trade_name, "area_sqm": l.total_area, "share_pct": round(amt / flt(self.total_expense) * 100, 4), "amount": amt})
		self.landlord_share = landlord
		self.status = "Allocated"
		self.save()
		return len(self.lines)
