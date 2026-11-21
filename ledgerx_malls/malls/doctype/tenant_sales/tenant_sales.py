import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from ledgerx_malls.engine.billing import month_end, month_start
from ledgerx_malls.engine.stats import sales_per_sqm

VERIFIERS = {"Mall Manager", "Mall Accountant", "System Manager"}


class TenantSales(Document):
	def validate(self):
		lease = frappe.db.get_value("Mall Lease", self.lease, ["docstatus", "start_date", "end_date", "total_area"], as_dict=1)
		if lease.docstatus != 1:
			frappe.throw(_("The lease must be submitted first"))
		self.month = month_start(getdate(self.month))
		if self.month > getdate(lease.end_date) or month_end(self.month) < getdate(lease.start_date):
			frappe.throw(_("{0} is outside the lease dates").format(self.month.strftime("%B %Y")))
		if flt(self.gross_sales) < 0 or flt(self.returns) < 0:
			frappe.throw(_("Amounts cannot be negative"))
		if flt(self.returns) > flt(self.gross_sales):
			frappe.throw(_("Returns cannot be more than the gross sales"))
		self.net_sales = round(flt(self.gross_sales) - flt(self.returns), 2)
		self.total_area = lease.total_area
		self.sales_per_sqm = sales_per_sqm(self.net_sales, flt(lease.total_area))
		other = frappe.db.exists("Tenant Sales", {"lease": self.lease, "month": ["between", [self.month, month_end(self.month)]], "name": ["!=", self.name]})
		if other:
			frappe.throw(_("Sales for {0} were already entered in {1}").format(self.month.strftime("%B %Y"), other))
		before = self.get_doc_before_save()
		if self.status == "Verified" and (not before or before.status != "Verified"):
			if not (VERIFIERS & set(frappe.get_roles())):
				frappe.throw(_("Only a mall manager or accountant can mark sales as verified"))
		elif before and before.status == "Verified" and (flt(before.net_sales) != flt(self.net_sales)):
			if not (VERIFIERS & set(frappe.get_roles())):
				frappe.throw(_("Verified sales can only be changed by a mall manager or accountant"))
			self.status = "Declared"
			frappe.msgprint(_("The sales changed, so they are Declared again until checked."), indicator="orange", alert=True)
