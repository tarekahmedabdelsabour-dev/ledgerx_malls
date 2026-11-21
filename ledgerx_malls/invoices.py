"""Hooks on Sales Invoice: give back what an invoice consumed when it is cancelled or deleted, and mark late fees charged when the invoice is submitted."""
import frappe
from frappe.utils import flt


def on_submit(doc, method=None):
	for it in doc.get("items") or []:
		src, through = it.get("ml_source"), it.get("ml_through")
		if src and through and frappe.db.exists("Sales Invoice", src):
			cur = frappe.db.get_value("Sales Invoice", src, "ml_late_fee_until")
			if not cur or str(through) > str(cur):
				frappe.db.set_value("Sales Invoice", src, "ml_late_fee_until", through, update_modified=False)


def _release(doc):
	frappe.db.sql("update `tabMeter Reading` set billed = 0, sales_invoice = null where sales_invoice = %s", doc.name)
	frappe.db.sql("update `tabCAM Line` set billed = 0, sales_invoice = null where sales_invoice = %s", doc.name)
	for alloc in frappe.get_all("CAM Allocation", filters={"status": "Billed"}, pluck="name"):
		if frappe.db.exists("CAM Line", {"parent": alloc, "billed": 0}):
			frappe.db.set_value("CAM Allocation", alloc, "status", "Allocated", update_modified=False)
	for it in doc.get("items") or []:
		src = it.get("ml_source")
		if src and it.get("ml_through") and frappe.db.exists("Sales Invoice", src):
			prev = frappe.db.sql(
				"""select max(i.ml_through) from `tabSales Invoice Item` i join `tabSales Invoice` s on s.name = i.parent
				where i.ml_source = %s and s.docstatus = 1 and s.name != %s""", (src, doc.name))[0][0]
			frappe.db.set_value("Sales Invoice", src, "ml_late_fee_until", prev, update_modified=False)


def on_cancel(doc, method=None):
	_release(doc)


def on_trash(doc, method=None):
	if doc.get("ml_lease") or doc.get("ml_mall"):
		_release(doc)
