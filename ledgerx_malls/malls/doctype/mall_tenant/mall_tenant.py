import frappe
from frappe import _
from frappe.model.document import Document


class MallTenant(Document):
	def before_validate(self):
		if self.customer:
			return
		existing = frappe.db.get_value("Customer", {"customer_name": self.tenant_name}, "name")
		if existing:
			self.customer = existing
			return
		group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
		territory = frappe.db.get_value("Territory", {"is_group": 0}, "name")
		if not (group and territory):
			frappe.throw(_("Create a customer group and a territory first, or choose the customer account yourself"))
		c = frappe.get_doc({"doctype": "Customer", "customer_name": self.tenant_name, "customer_type": "Company", "customer_group": group, "territory": territory, "tax_id": self.tax_id})
		c.insert(ignore_permissions=True)
		self.customer = c.name
