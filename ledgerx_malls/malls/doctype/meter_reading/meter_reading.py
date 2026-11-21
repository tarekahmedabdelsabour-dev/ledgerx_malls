import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from ledgerx_malls import data


class MeterReading(Document):
	def validate(self):
		m = frappe.db.get_value("Utility Meter", self.meter, ["unit", "multiplier", "rate", "opening_reading", "active", "utility"], as_dict=1)
		if not m.active:
			frappe.throw(_("Meter {0} is not active").format(self.meter))
		prev = frappe.db.sql("select reading from `tabMeter Reading` where meter = %s and reading_date <= %s and name != %s order by reading_date desc, creation desc limit 1",
			(self.meter, self.reading_date, self.name or ""))
		prev = flt(prev[0][0]) if prev else flt(m.opening_reading)
		if flt(self.reading) < prev:
			frappe.throw(_("The reading cannot be lower than the previous one ({0}). If the meter was replaced, set a new meter.").format(prev))
		self.previous_reading = prev
		self.consumption = round((flt(self.reading) - prev) * flt(m.multiplier or 1), 4)
		self.amount = round(self.consumption * flt(m.rate), 2)
		self.unit = m.unit
		self.utility = m.utility
		if not self.billed:
			d = getdate(self.reading_date)
			row = frappe.db.sql(
				"""select l.name from `tabMall Lease` l join `tabLease Unit` u on u.parent = l.name where l.docstatus = 1 and u.unit = %s and l.start_date <= %s
				and least(l.end_date, ifnull(l.terminated_on, l.end_date)) >= %s limit 1""", (m.unit, d, d))
			self.lease = row[0][0] if row else None
			if not self.lease and flt(self.amount):
				frappe.msgprint(_("No lease is in force on this unit at that date, so the amount stays with the landlord."), indicator="orange", alert=True)

	def on_trash(self):
		if self.billed:
			frappe.throw(_("This reading was billed on {0}. Cancel or delete that invoice first.").format(self.sales_invoice))
