import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from ledgerx_malls import data


class MallUnit(Document):
	def validate(self):
		if flt(self.area_sqm) <= 0:
			frappe.throw(_("The area must be more than zero"))
		if self.floor and frappe.db.get_value("Mall Floor", self.floor, "mall") != self.mall:
			frappe.throw(_("Floor {0} belongs to another mall").format(self.floor))
		if self.status in ("Occupied", "Fit-out") and not self.current_lease:
			frappe.throw(_("Occupied and Fit-out follow the lease: create a lease for this unit instead"))

	def on_update(self):
		data.update_mall_totals(self.mall)

	def on_trash(self):
		if frappe.db.exists("Lease Unit", {"unit": self.name}):
			frappe.throw(_("This unit appears in a lease and cannot be deleted. Set it inactive instead."))
