"""Builds every DocType JSON of ledgerx_malls from the compact table below.
Run from the repo root:  python3 tools/gen_doctypes.py   (rewrites ledgerx_malls/pharmacy/doctype/*/*.json; controller .py files are never overwritten)"""
import json
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..", "ledgerx_malls", "malls", "doctype")
TS = "2026-11-22 08:00:00.000000"
MODULE = "Malls"
def f(name, ftype, label=None, **kw):
	d = {"fieldname": name, "fieldtype": ftype}
	if ftype not in ("Section Break", "Column Break", "Tab Break"):
		d["label"] = label or name.replace("_", " ").title()
	elif label:
		d["label"] = label
	d.update(kw)
	return d


def sec(name, label=None, **kw):
	return f(name, "Section Break", label, **kw)


def col(name):
	return f(name, "Column Break")


def perms(*rows):
	"""mode: r | rw | rwc | all | sub (rwc + submit) | full (all + submit/cancel/amend)"""
	out = []
	for role, mode in rows:
		p = {"role": role, "read": 1, "report": 1, "print": 1, "export": 1}
		if mode in ("rw", "rwc", "all", "sub", "full"):
			p["write"] = 1
		if mode in ("rwc", "all", "sub", "full"):
			p["create"] = 1
		if mode in ("all", "full"):
			p["delete"] = 1
		if mode in ("sub", "full"):
			p["submit"] = 1
		if mode == "full":
			p.update({"cancel": 1, "amend": 1})
		out.append(p)
	out.append({"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "print": 1, "export": 1})
	return out


MGR, LO, ACC, OPS = "Mall Manager", "Leasing Officer", "Mall Accountant", "Mall Operations"

DT = {}


def doctype(name, fields, **kw):
	DT[name] = {"name": name, "fields": fields, **kw}


UNIT_STATUS = "Vacant\nReserved\nOccupied\nFit-out\nMaintenance"
CHARGES = "Rent\nService Charge\nMarketing Fund\nUtilities\nTurnover Rent\nCAM Reconciliation\nLate Fee"
UTIL = "Electricity\nWater\nAir Conditioning\nGas"

# ------------------------------------------------------------------ settings and master data
doctype("Mall Settings", [
	f("company", "Link", "Company", options="Company"),
	f("sales_taxes_template", "Link", "Sales Taxes Template", options="Sales Taxes and Charges Template", description="Added to every rent invoice. Leave empty when not taxed."),
	f("invoice_due_days", "Int", "Invoice Due After (days)", default=7),
	sec("sb_items", "Billing Items"),
	f("rent_item", "Link", "Rent Item", options="Item"),
	f("service_item", "Link", "Service Charge Item", options="Item"),
	f("marketing_item", "Link", "Marketing Fund Item", options="Item"),
	f("utility_item", "Link", "Utilities Item", options="Item"),
	f("turnover_item", "Link", "Turnover Rent Item", options="Item"),
	f("cam_item", "Link", "Expense Recovery Item", options="Item"),
	f("late_fee_item", "Link", "Late Fee Item", options="Item"),
	sec("sb_late", "Late Payment"),
	f("late_fee_grace_days", "Int", "Grace Days Before a Late Fee", default=5),
	f("late_fee_pct_month", "Percent", "Late Fee % per Month", default=0, description="0 = no late fees."),
	sec("sb_sales", "Tenant Sales"),
	f("turnover_needs_verified", "Check", "Turnover Rent Only on Verified Sales", default=1, description="Declared sales that nobody checked are left out of the invoice and flagged."),
	sec("sb_alerts", "Alerts"),
	f("expiry_alert_days", "Int", "Warn About Leases Ending Within (days)", default=180),
], issingle=1, icon="fa fa-building", perms=perms((MGR, "rw"), (ACC, "r"), (LO, "r")))

doctype("Mall Category", [f("category_name", "Data", "Category", reqd=1, unique=1, in_list_view=1)], autoname="field:category_name",
	perms=perms((MGR, "all"), (LO, "rwc"), (ACC, "r"), (OPS, "r")))

doctype("Mall", [
	f("mall_name", "Data", "Mall Name", reqd=1, unique=1, in_list_view=1),
	f("company", "Link", "Company", options="Company", reqd=1, in_list_view=1),
	f("active", "Check", "Active", default=1, in_list_view=1),
	col("cb1"),
	f("cost_center", "Link", "Cost Center", options="Cost Center", description="Income and costs of this mall are reported here."),
	f("manager", "Link", "Mall Manager", options="Employee"),
	f("manager_user", "Data", "Manager User", read_only=1, fetch_from="manager.user_id"),
	sec("sb_a", "Address"),
	f("city", "Data", "City"),
	f("address", "Small Text", "Address"),
	f("opening_date", "Date", "Opening Date"),
	sec("sb_t", "Totals (calculated)"),
	f("total_gla", "Float", "Total Lettable Area (sqm)", read_only=1),
	f("occupied_area", "Float", "Occupied Area (sqm)", read_only=1),
	f("occupancy_pct", "Percent", "Occupancy %", read_only=1),
], autoname="field:mall_name", title_field="mall_name", icon="fa fa-building", perms=perms((MGR, "all"), (LO, "r"), (ACC, "r"), (OPS, "r")))

doctype("Mall Floor", [
	f("mall", "Link", "Mall", options="Mall", reqd=1, in_list_view=1, in_standard_filter=1),
	f("floor_name", "Data", "Floor", reqd=1, in_list_view=1),
	f("level", "Int", "Level No.", description="0 = ground, -1 = basement."),
], autoname="format:{mall}-{floor_name}", title_field="floor_name", perms=perms((MGR, "all"), (LO, "rwc"), (OPS, "r")))

doctype("Mall Unit", [
	f("unit_no", "Data", "Unit No.", reqd=1, in_list_view=1),
	f("mall", "Link", "Mall", options="Mall", reqd=1, in_list_view=1, in_standard_filter=1),
	f("floor", "Link", "Floor", options="Mall Floor", in_list_view=1, in_standard_filter=1),
	f("category", "Link", "Category", options="Mall Category", in_standard_filter=1),
	col("cb1"),
	f("area_sqm", "Float", "Area (sqm)", reqd=1, in_list_view=1),
	f("list_rent_sqm", "Currency", "Asking Rent per sqm per Month"),
	f("is_anchor", "Check", "Anchor Store"),
	f("active", "Check", "Active", default=1),
	sec("sb_s", "Status"),
	f("status", "Select", "Status", options=UNIT_STATUS, default="Vacant", in_list_view=1, in_standard_filter=1, description="Occupied and Fit-out follow the lease; the rest you set."),
	f("current_lease", "Link", "Current Lease", options="Mall Lease", read_only=1),
	f("current_tenant", "Link", "Current Tenant", options="Mall Tenant", read_only=1, in_list_view=1),
	f("notes", "Small Text", "Notes"),
], autoname="format:{mall}-{unit_no}", title_field="unit_no", icon="fa fa-th-large", search_fields="unit_no,mall",
	perms=perms((MGR, "all"), (LO, "rwc"), (ACC, "r"), (OPS, "rw")))

doctype("Mall Tenant", [
	f("tenant_name", "Data", "Legal Name", reqd=1, in_list_view=1),
	f("trade_name", "Data", "Brand / Trade Name", reqd=1, in_list_view=1, in_standard_filter=1),
	f("customer", "Link", "Customer Account", options="Customer", description="Invoices go to this customer. Created automatically when left empty."),
	f("category", "Link", "Category", options="Mall Category", in_standard_filter=1),
	f("status", "Select", "Status", options="Active\nOn Hold\nFormer", default="Active", in_list_view=1),
	col("cb1"),
	f("commercial_register", "Data", "Commercial Register No."),
	f("tax_id", "Data", "Tax ID"),
	f("contact_person", "Data", "Contact Person"),
	f("phone", "Data", "Phone"),
	f("email", "Data", "Email"),
	sec("sb_g", "Guarantee"),
	f("guarantor", "Data", "Guarantor"),
	f("notes", "Small Text", "Notes"),
], autoname="format:TNT-.#####", title_field="trade_name", icon="fa fa-shopping-bag", search_fields="trade_name,tenant_name",
	perms=perms((MGR, "all"), (LO, "rwc"), (ACC, "rw"), (OPS, "r")))

# ------------------------------------------------------------------ leases
doctype("Lease Unit", [
	f("unit", "Link", "Unit", options="Mall Unit", reqd=1, in_list_view=1),
	f("area_sqm", "Float", "Area (sqm)", read_only=1, in_list_view=1, fetch_from="unit.area_sqm"),
], istable=1)

doctype("Lease Free Period", [
	f("from_date", "Date", "From", reqd=1, in_list_view=1),
	f("to_date", "Date", "To", reqd=1, in_list_view=1),
	f("applies_to", "Select", "Applies To", options="All\nRent\nService Charge", default="All", in_list_view=1),
	f("note", "Data", "Note"),
], istable=1)

doctype("Mall Lease", [
	f("mall", "Link", "Mall", options="Mall", reqd=1, in_list_view=1, in_standard_filter=1),
	f("tenant", "Link", "Tenant", options="Mall Tenant", reqd=1, in_list_view=1, in_standard_filter=1),
	f("trade_name", "Data", "Brand", read_only=1, fetch_from="tenant.trade_name", in_list_view=1),
	col("cb1"),
	f("start_date", "Date", "Lease Start", reqd=1, in_list_view=1),
	f("end_date", "Date", "Lease End", reqd=1, in_list_view=1),
	f("lease_status", "Select", "Lease Status", options="Upcoming\nActive\nExpired\nTerminated", default="Upcoming", read_only=1, in_list_view=1, in_standard_filter=1),
	sec("sb_u", "Units"),
	f("units", "Table", "Units", options="Lease Unit", reqd=1),
	f("total_area", "Float", "Total Area (sqm)", read_only=1),
	sec("sb_r", "Rent"),
	f("rent_model", "Select", "Rent Model", options="Fixed\nPercentage of Sales\nHigher of Fixed and Percentage", default="Fixed", reqd=1, in_list_view=1),
	f("rent_basis", "Select", "Rent Is Entered", options="Per sqm per Month\nFixed Amount per Month", default="Per sqm per Month", depends_on="eval:doc.rent_model!='Percentage of Sales'"),
	f("rent_amount", "Currency", "Rent Amount", depends_on="eval:doc.rent_model!='Percentage of Sales'"),
	f("base_rent", "Currency", "Base Rent per Month", read_only=1, description="Before escalation and free periods."),
	col("cb2"),
	f("rent_escalation_pct", "Percent", "Yearly Rent Increase %", description="Applied on every lease anniversary."),
	f("turnover_pct", "Percent", "Percentage of Sales %", depends_on="eval:doc.rent_model!='Fixed'", mandatory_depends_on="eval:doc.rent_model!='Fixed'"),
	sec("sb_c", "Service Charge and Marketing"),
	f("service_per_sqm", "Currency", "Service Charge per sqm per Month"),
	f("service_escalation_pct", "Percent", "Yearly Service Charge Increase %"),
	col("cb3"),
	f("marketing_pct", "Percent", "Marketing Fund % of Base Rent"),
	f("recover_cam", "Check", "Takes Part in Expense Recovery", default=1, description="Share of the common-area expenses allocated by area."),
	sec("sb_f", "Rent-free Periods (fit-out and incentives)"),
	f("free_periods", "Table", "Rent-free Periods", options="Lease Free Period"),
	sec("sb_d", "Security Deposit"),
	f("security_deposit", "Currency", "Security Deposit"),
	f("deposit_status", "Select", "Deposit Status", options="Pending\nReceived\nRefunded\nForfeited", default="Pending"),
	sec("sb_e", "End of Lease"),
	f("terminated_on", "Date", "Terminated On", read_only=1),
	f("termination_reason", "Small Text", "Termination Reason", read_only=1),
	f("renewed_from", "Link", "Renewal Of", options="Mall Lease", read_only=1, no_copy=1),
	f("company", "Link", "Company", options="Company", read_only=1, fetch_from="mall.company"),
	f("amended_from", "Link", "Amended From", options="Mall Lease", read_only=1, no_copy=1, print_hide=1),
], autoname="format:LSE-.YYYY.-.#####", is_submittable=1, title_field="trade_name", icon="fa fa-file-text-o",
	perms=perms((MGR, "full"), (LO, "sub"), (ACC, "r"), (OPS, "r")))

# ------------------------------------------------------------------ meters
doctype("Utility Meter", [
	f("meter_no", "Data", "Meter No.", reqd=1, in_list_view=1),
	f("mall", "Link", "Mall", options="Mall", reqd=1, in_standard_filter=1),
	f("unit", "Link", "Unit", options="Mall Unit", reqd=1, in_list_view=1, in_standard_filter=1),
	f("utility", "Select", "Utility", options=UTIL, reqd=1, in_list_view=1, in_standard_filter=1),
	col("cb1"),
	f("multiplier", "Float", "Multiplier", default=1),
	f("rate", "Currency", "Price per Unit", reqd=1, in_list_view=1),
	f("opening_reading", "Float", "Opening Reading"),
	f("active", "Check", "Active", default=1),
], autoname="format:{mall}-{meter_no}", title_field="meter_no", perms=perms((MGR, "all"), (OPS, "all"), (ACC, "r"), (LO, "r")))

doctype("Meter Reading", [
	f("meter", "Link", "Meter", options="Utility Meter", reqd=1, in_list_view=1, in_standard_filter=1),
	f("reading_date", "Date", "Reading Date", reqd=1, default="Today", in_list_view=1),
	f("reading", "Float", "Reading", reqd=1, in_list_view=1),
	col("cb1"),
	f("previous_reading", "Float", "Previous Reading", read_only=1),
	f("consumption", "Float", "Consumption", read_only=1, in_list_view=1),
	f("amount", "Currency", "Amount", read_only=1, in_list_view=1),
	sec("sb_l", "Billing"),
	f("unit", "Link", "Unit", options="Mall Unit", read_only=1, fetch_from="meter.unit"),
	f("utility", "Data", "Utility", read_only=1, fetch_from="meter.utility"),
	f("lease", "Link", "Lease", options="Mall Lease", read_only=1),
	f("billed", "Check", "Billed", read_only=1, in_standard_filter=1),
	f("sales_invoice", "Link", "Sales Invoice", options="Sales Invoice", read_only=1),
], autoname="format:MTR-.YYYY.-.#####", icon="fa fa-tachometer", perms=perms((MGR, "all"), (OPS, "all"), (ACC, "r")))

# ------------------------------------------------------------------ sales and visitors
doctype("Tenant Sales", [
	f("lease", "Link", "Lease", options="Mall Lease", reqd=1, in_list_view=1, in_standard_filter=1),
	f("month", "Date", "Month", reqd=1, in_list_view=1, description="Any day of the month."),
	f("gross_sales", "Currency", "Gross Sales", reqd=1, in_list_view=1),
	f("returns", "Currency", "Returns and Cancellations"),
	f("net_sales", "Currency", "Net Sales", read_only=1, in_list_view=1),
	col("cb1"),
	f("status", "Select", "Status", options="Declared\nVerified", default="Declared", in_list_view=1, in_standard_filter=1, description="Only a manager or an accountant can mark sales as verified."),
	f("evidence", "Small Text", "How It Was Checked"),
	sec("sb_l", "Lease"),
	f("mall", "Link", "Mall", options="Mall", read_only=1, fetch_from="lease.mall"),
	f("tenant", "Link", "Tenant", options="Mall Tenant", read_only=1, fetch_from="lease.tenant"),
	f("total_area", "Float", "Area (sqm)", read_only=1),
	f("sales_per_sqm", "Currency", "Sales per sqm", read_only=1),
], autoname="format:TSL-.YYYY.-.#####", icon="fa fa-line-chart", perms=perms((MGR, "all"), (ACC, "all"), (LO, "rwc"), (OPS, "r")))

doctype("Footfall", [
	f("mall", "Link", "Mall", options="Mall", reqd=1, in_list_view=1, in_standard_filter=1),
	f("date", "Date", "Date", reqd=1, default="Today", in_list_view=1),
	f("entrance", "Data", "Entrance / Counter", default="Main"),
	f("visitors", "Int", "Visitors", reqd=1, in_list_view=1),
	f("note", "Data", "Note"),
], autoname="hash", icon="fa fa-users", perms=perms((MGR, "all"), (OPS, "all"), (ACC, "r"), (LO, "r")))

# ------------------------------------------------------------------ expense recovery
doctype("CAM Line", [
	f("lease", "Link", "Lease", options="Mall Lease", reqd=1, in_list_view=1),
	f("trade_name", "Data", "Brand", read_only=1, in_list_view=1),
	f("area_sqm", "Float", "Area (sqm)", read_only=1, in_list_view=1),
	f("share_pct", "Percent", "Share %", read_only=1, in_list_view=1),
	f("amount", "Currency", "Amount", read_only=1, in_list_view=1),
	f("billed", "Check", "Billed", read_only=1),
	f("sales_invoice", "Link", "Sales Invoice", options="Sales Invoice", read_only=1),
], istable=1)

doctype("CAM Allocation", [
	f("mall", "Link", "Mall", options="Mall", reqd=1, in_list_view=1, in_standard_filter=1),
	f("from_date", "Date", "From", reqd=1, in_list_view=1),
	f("to_date", "Date", "To", reqd=1, in_list_view=1),
	col("cb1"),
	f("total_expense", "Currency", "Expenses to Recover", reqd=1, in_list_view=1, description="Type it, or press Load Expenses to read the mall's expense accounts."),
	f("landlord_bears_vacant", "Check", "Landlord Bears the Vacant Space", default=1),
	sec("sb_l", "Allocation"),
	f("lines", "Table", "Allocation", options="CAM Line"),
	f("landlord_share", "Currency", "Landlord Share (vacant space)", read_only=1),
	f("status", "Select", "Status", options="Draft\nAllocated\nBilled", default="Draft", read_only=1, in_list_view=1, in_standard_filter=1),
	f("company", "Link", "Company", options="Company", read_only=1, fetch_from="mall.company"),
], autoname="format:CAM-.YYYY.-.#####", icon="fa fa-pie-chart", perms=perms((MGR, "all"), (ACC, "all")))

# ------------------------------------------------------------------ billing
doctype("Billing Line", [
	f("include", "Check", "Bill", default=1, in_list_view=1),
	f("lease", "Link", "Lease", options="Mall Lease", read_only=1, in_list_view=1),
	f("trade_name", "Data", "Brand", read_only=1, in_list_view=1),
	f("charge_type", "Select", "Charge", options=CHARGES, read_only=1, in_list_view=1),
	f("description", "Data", "Description", read_only=1),
	f("amount", "Currency", "Amount", in_list_view=1),
	f("source", "Data", "Source", read_only=1, description="The record this charge came from."),
	f("note", "Data", "Note", read_only=1),
], istable=1)

doctype("Mall Billing Run", [
	f("mall", "Link", "Mall", options="Mall", reqd=1, in_list_view=1, in_standard_filter=1),
	f("billing_month", "Date", "Month to Bill", reqd=1, in_list_view=1, description="Any day of the month: rent and service charge are billed for this month."),
	f("posting_date", "Date", "Invoice Date", reqd=1, default="Today"),
	col("cb1"),
	f("bill_turnover", "Check", "Add Turnover Rent of the Previous Month", default=1),
	f("bill_utilities", "Check", "Add Meter Readings Not Yet Billed", default=1),
	f("bill_cam", "Check", "Add Expense Recovery Not Yet Billed", default=1),
	f("bill_late_fees", "Check", "Add Late Fees", default=1),
	sec("sb_l", "Charges"),
	f("lines", "Table", "Charges", options="Billing Line"),
	sec("sb_r", "Result"),
	f("status", "Select", "Status", options="Draft\nPrepared\nInvoiced", default="Draft", read_only=1, in_list_view=1, in_standard_filter=1),
	f("total_amount", "Currency", "Total to Bill", read_only=1, in_list_view=1),
	f("invoices_made", "Small Text", "Invoices Created", read_only=1),
	f("notes_html", "Text Editor", "Notes", read_only=1),
	f("company", "Link", "Company", options="Company", read_only=1, fetch_from="mall.company"),
], autoname="format:MBR-.YYYY.-.#####", icon="fa fa-calculator", perms=perms((MGR, "all"), (ACC, "all")))


def build():
	os.makedirs(ROOT, exist_ok=True)
	for name, d in DT.items():
		fields = d["fields"]
		order = [x["fieldname"] for x in fields]
		istable = d.get("istable", 0)
		out = {
			"actions": [], "creation": TS, "doctype": "DocType", "engine": "InnoDB", "field_order": order, "fields": fields,
			"links": [], "modified": TS, "modified_by": "Administrator", "module": MODULE, "name": name, "owner": "Administrator",
			"sort_field": "creation", "sort_order": "DESC", "states": [],
			"permissions": [] if istable else d.get("perms", []),
		}
		for k in ("autoname", "title_field", "icon", "track_changes", "issingle", "istable", "show_title_field_in_link", "search_fields", "is_submittable"):
			if k in d:
				out[k] = d[k]
		if not istable:
			out["track_changes"] = 1  # who changed what, when
		if "autoname" not in d and not istable and not d.get("issingle"):
			out["autoname"] = "hash"
		out["allow_rename"] = 0
		slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
		folder = os.path.join(ROOT, slug)
		os.makedirs(folder, exist_ok=True)
		open(os.path.join(folder, "__init__.py"), "a").close()
		with open(os.path.join(folder, slug + ".json"), "w", encoding="utf-8") as fh:
			json.dump(out, fh, indent=1, ensure_ascii=False)
			fh.write("\n")
		py = os.path.join(folder, slug + ".py")
		if not os.path.exists(py):
			cls = "".join(w.capitalize() for w in re.split(r"[^A-Za-z0-9]+", name))
			with open(py, "w") as fh:
				fh.write(f"from frappe.model.document import Document\n\n\nclass {cls}(Document):\n\tpass\n")


if __name__ == "__main__":
	build()
	print(len(DT), "doctypes")
