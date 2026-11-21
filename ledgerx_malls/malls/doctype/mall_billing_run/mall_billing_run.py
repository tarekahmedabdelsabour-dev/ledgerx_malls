from collections import OrderedDict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, getdate, nowdate

from ledgerx_malls import data
from ledgerx_malls.engine.billing import add_months, base_rent_applies, late_fee, month_end, month_start, monthly_charge, percentage_rent

ITEM_FIELD = {"Rent": "rent_item", "Service Charge": "service_item", "Marketing Fund": "marketing_item", "Utilities": "utility_item", "Turnover Rent": "turnover_item",
	"CAM Reconciliation": "cam_item", "Late Fee": "late_fee_item"}


class MallBillingRun(Document):
	def validate(self):
		self.billing_month = month_start(getdate(self.billing_month))
		self.total_amount = round(sum(flt(l.amount) for l in self.lines if l.include), 2)

	# ------------------------------------------------------------------ prepare
	@frappe.whitelist()
	def prepare(self):
		"""Works out every charge of the month for the mall's leases. Nothing is invoiced yet: review the lines, untick or change what you need."""
		self.check_permission("write")
		if self.status == "Invoiced":
			frappe.throw(_("This run is already invoiced"))
		if not frappe.db.get_value("Mall", self.mall, "active"):
			frappe.throw(_("Mall {0} is not active").format(self.mall))
		s = data.settings()
		month = month_start(getdate(self.billing_month))
		last = month_end(month)
		prev = add_months(month, -1)
		posting = getdate(self.posting_date)
		self.lines = []
		notes = []
		leases = data.leases_in_force(self.mall, month, last)
		if not leases:
			notes.append(_("No lease is in force in {0}.").format(month.strftime("%B %Y")))
		for l in leases:
			dup = frappe.db.get_value("Sales Invoice", {"ml_lease": l.name, "ml_period": month, "docstatus": ["<", 2]}, "name")
			if dup:
				notes.append(_("{0} ({1}) was already invoiced for {2} in {3}: skipped.").format(l.trade_name, l.name, month.strftime("%B %Y"), dup))
				continue
			t = data.lease_terms(l)
			name = l.trade_name
			rent = 0.0
			if base_rent_applies(t["model"]) and t["base"] > 0:
				rent = monthly_charge(t["base"], t["esc"], t["start"], t["end"], month, t["free"], "Rent")
				if rent > 0:
					self._add(l, "Rent", _("Rent {0}").format(month.strftime("%B %Y")), rent)
			if t["service"] > 0:
				svc = monthly_charge(t["service"], t["service_esc"], t["start"], t["end"], month, t["free"], "Service Charge")
				if svc > 0:
					self._add(l, "Service Charge", _("Service charge {0}").format(month.strftime("%B %Y")), svc)
			if t["marketing_pct"] > 0 and rent > 0:
				self._add(l, "Marketing Fund", _("Marketing fund {0}% of rent {1}").format(t["marketing_pct"], month.strftime("%B %Y")), round(rent * t["marketing_pct"] / 100.0, 2))
			if self.bill_turnover and t["model"] != "Fixed":
				self._turnover(l, t, prev, s, notes)
			if self.bill_utilities:
				for r in frappe.get_all("Meter Reading", filters={"lease": l.name, "billed": 0, "reading_date": ["<=", posting]}, fields=["name", "utility", "meter", "consumption", "amount", "reading_date"], order_by="reading_date"):
					if flt(r.amount) > 0:
						self._add(l, "Utilities", _("{0} {1}: {2} units").format(r.utility, r.meter, flt(r.consumption, 2)), flt(r.amount), source=r.name)
			if self.bill_cam:
				for row in frappe.db.sql("""select c.name, c.parent, c.amount from `tabCAM Line` c join `tabCAM Allocation` a on a.name = c.parent
					where c.lease = %s and c.billed = 0 and a.status = 'Allocated' and a.mall = %s""", (l.name, self.mall), as_dict=True):
					if flt(row.amount) > 0:
						self._add(l, "CAM Reconciliation", _("Share of common-area expenses ({0})").format(row.parent), flt(row.amount), source=f"{row.parent}|{row.name}")
			if self.bill_late_fees and flt(s.late_fee_pct_month) > 0:
				self._late_fees(l, s, posting)
		self.status = "Prepared"
		self.notes_html = "<br>".join(frappe.utils.escape_html(n) for n in notes) if notes else _("Review the lines, then create the invoices.")
		self.validate()
		self.save()
		return len(self.lines)

	def _add(self, lease, kind, desc, amount, source=None, include=1, note=None):
		self.append("lines", {"lease": lease.name, "trade_name": lease.trade_name, "charge_type": kind, "description": desc, "amount": round(amount, 2), "source": source, "include": include, "note": note})

	def _turnover(self, l, t, prev, s, notes):
		rows = frappe.get_all("Tenant Sales", filters={"lease": l.name, "month": ["between", [prev, month_end(prev)]]}, fields=["name", "net_sales", "status"])
		if not rows:
			notes.append(_("{0}: no sales entered for {1}, so no turnover rent was calculated.").format(l.trade_name, prev.strftime("%B %Y")))
			return
		net = sum(flt(r.net_sales) for r in rows)
		base_prev = monthly_charge(t["base"], t["esc"], t["start"], t["end"], prev, t["free"], "Rent") if base_rent_applies(t["model"]) else 0.0
		amt = percentage_rent(t["model"], t["turnover_pct"], net, base_prev)
		if amt <= 0:
			return
		verified = all(r.status == "Verified" for r in rows)
		inc = 1 if (verified or not s.turnover_needs_verified) else 0
		self._add(l, "Turnover Rent", _("Turnover rent {0}% of sales {1} ({2})").format(t["turnover_pct"], prev.strftime("%B %Y"), frappe.format_value(net, {"fieldtype": "Currency"})), amt,
			source=rows[0].name, include=inc, note=None if inc else _("Sales not verified yet"))
		if not inc:
			notes.append(_("{0}: turnover rent {1} left unticked because the sales are not verified.").format(l.trade_name, amt))

	def _late_fees(self, l, s, posting):
		customer = frappe.db.get_value("Mall Tenant", l.tenant, "customer")
		for inv in frappe.get_all("Sales Invoice", filters={"customer": customer, "ml_lease": l.name, "docstatus": 1, "outstanding_amount": [">", 0], "due_date": ["<", posting]},
			fields=["name", "due_date", "outstanding_amount", "ml_late_fee_until"]):
			fee, through = late_fee(flt(inv.outstanding_amount), getdate(inv.due_date), s.late_fee_grace_days, posting, flt(s.late_fee_pct_month), getdate(inv.ml_late_fee_until) if inv.ml_late_fee_until else None)
			if fee > 0:
				self._add(l, "Late Fee", _("Late fee on {0} through {1}").format(inv.name, through), fee, source=f"{inv.name}|{through}")

	# ------------------------------------------------------------------ invoices
	@frappe.whitelist()
	def create_invoices(self):
		"""One draft Sales Invoice per lease. Drafts leave room for a last look; submit them from the Submit Invoices button."""
		self.check_permission("write")
		if self.status != "Prepared":
			frappe.throw(_("Prepare the run first"))
		s = data.settings()
		for kind, fld in ITEM_FIELD.items():
			if any(l.include and l.charge_type == kind and flt(l.amount) > 0 for l in self.lines) and not s.get(fld):
				frappe.throw(_("Set the {0} in Mall Settings").format(frappe.get_meta("Mall Settings").get_label(fld)))
		groups = OrderedDict()
		for l in self.lines:
			if l.include and flt(l.amount) > 0:
				groups.setdefault(l.lease, []).append(l)
		if not groups:
			frappe.throw(_("Nothing is ticked to bill"))
		mall = frappe.get_doc("Mall", self.mall)
		month = month_start(getdate(self.billing_month))
		made = []
		for lease_name, lines in groups.items():
			lease = frappe.get_doc("Mall Lease", lease_name)
			customer = frappe.db.get_value("Mall Tenant", lease.tenant, "customer")
			si = frappe.new_doc("Sales Invoice")
			si.customer = customer
			si.company = mall.company
			si.posting_date = self.posting_date
			si.set_posting_time = 1
			si.due_date = add_days(self.posting_date, int(s.invoice_due_days or 0))
			if mall.cost_center:
				si.cost_center = mall.cost_center
			si.ml_mall, si.ml_lease, si.ml_period = self.mall, lease_name, month
			si.remarks = _("Mall billing run {0}").format(self.name)
			for l in lines:
				row = {"item_code": s.get(ITEM_FIELD[l.charge_type]), "qty": 1, "rate": flt(l.amount), "description": f"{l.description}\n{lease.trade_name} - {', '.join(u.unit for u in lease.units)}"}
				if mall.cost_center:
					row["cost_center"] = mall.cost_center
				if l.charge_type == "Late Fee" and l.source and "|" in l.source:
					src, through = l.source.split("|")
					row.update({"ml_source": src, "ml_through": through})
				si.append("items", row)
			if s.sales_taxes_template:
				si.taxes_and_charges = s.sales_taxes_template
				si.set_taxes()
			si.insert(ignore_permissions=True)
			made.append(si.name)
			for l in lines:
				if l.charge_type == "Utilities" and l.source:
					frappe.db.set_value("Meter Reading", l.source, {"billed": 1, "sales_invoice": si.name}, update_modified=False)
				elif l.charge_type == "CAM Reconciliation" and l.source and "|" in l.source:
					alloc, line = l.source.split("|")
					frappe.db.set_value("CAM Line", line, {"billed": 1, "sales_invoice": si.name}, update_modified=False)
					if not frappe.db.exists("CAM Line", {"parent": alloc, "billed": 0}):
						frappe.db.set_value("CAM Allocation", alloc, "status", "Billed", update_modified=False)
		self.invoices_made = "\n".join(made)
		self.status = "Invoiced"
		self.save()
		return made

	@frappe.whitelist()
	def submit_invoices(self):
		self.check_permission("write")
		n = 0
		for name in (self.invoices_made or "").split("\n"):
			if name and frappe.db.get_value("Sales Invoice", name, "docstatus") == 0:
				frappe.get_doc("Sales Invoice", name).submit()
				n += 1
		return n
