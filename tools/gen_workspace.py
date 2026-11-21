"""Writes the workspace, sidebar and dock JSON of ledgerx_malls. Run from the repo root."""
import json
import os
import uuid

BASE = os.path.join(os.path.dirname(__file__), "..", "ledgerx_malls")
TS = "2026-11-22 09:00:00.000000"  # raise this whenever the workspace changes: migrate only re-reads a file that is newer than the saved one
CARDS = [
	("Vacant Units", "Mall Unit", [["Mall Unit", "status", "=", "Vacant"], ["Mall Unit", "active", "=", 1]], "Count", None),
	("Leases Active", "Mall Lease", [["Mall Lease", "docstatus", "=", 1], ["Mall Lease", "lease_status", "=", "Active"]], "Count", None),
	("Leases Ending in 6 Months", "Mall Lease", [["Mall Lease", "docstatus", "=", 1], ["Mall Lease", "lease_status", "=", "Active"], ["Mall Lease", "end_date", "Timespan", "next 6 months"]], "Count", None),
	("Sales Awaiting Verification", "Tenant Sales", [["Tenant Sales", "status", "=", "Declared"]], "Count", None),
	("Billing Runs to Invoice", "Mall Billing Run", [["Mall Billing Run", "status", "=", "Prepared"]], "Count", None),
	("Unbilled Meter Readings", "Meter Reading", [["Meter Reading", "billed", "=", 0]], "Count", None),
]
CHARTS = [
	("Units by Status", "Mall Unit", "Donut", "group", {"by": "status"}),
	("Leases by Rent Model", "Mall Lease", "Donut", "group", {"by": "rent_model", "filters": [["Mall Lease", "docstatus", "=", 1]]}),
]
GROUPS = [
	("Leasing", None, 0, [
		("Mall Lease", "DocType", "Mall Lease", "file-text"), ("Mall Unit", "DocType", "Mall Unit", "layout-grid"), ("Mall Tenant", "DocType", "Mall Tenant", "store")]),
	("Billing", "calculator", 0, [
		("Mall Billing Run", "DocType", "Mall Billing Run", "calculator"), ("Tenant Sales", "DocType", "Tenant Sales", "trending-up"), ("CAM Allocation", "DocType", "CAM Allocation", "pie-chart"),
		("Sales Invoice", "DocType", "Sales Invoice", "file-text"), ("Payment Entry", "DocType", "Payment Entry", "banknote")]),
	("Operations", "wrench", 0, [
		("Meter Reading", "DocType", "Meter Reading", "gauge"), ("Utility Meter", "DocType", "Utility Meter", "gauge"), ("Footfall", "DocType", "Footfall", "users")]),
	("Reports", "bar-chart-3", 0, [
		("Rent Roll", "Report", "Rent Roll", "list"), ("Occupancy", "Report", "Occupancy", "pie-chart"), ("Tenant Aging", "Report", "Tenant Aging", "hourglass"),
		("Tenant Sales Performance", "Report", "Tenant Sales Performance", "trending-up"), ("Lease Expiry", "Report", "Lease Expiry", "calendar-clock"),
		("Footfall and Sales", "Report", "Footfall and Sales", "users"), ("Billing and Collection", "Report", "Billing and Collection", "banknote")]),
	("Setup", "settings", 0, [
		("Mall", "DocType", "Mall", "building"), ("Mall Floor", "DocType", "Mall Floor", "layers"), ("Mall Category", "DocType", "Mall Category", "tag"), ("Mall Settings", "DocType", "Mall Settings", "settings")]),
	("Source Data", "database", 1, [
		("Customer", "DocType", "Customer", "users"), ("Item", "DocType", "Item", "box"), ("Employee", "DocType", "Employee", "user")]),
]
TOP = ["Mall Lease", "Mall Billing Run", "Tenant Sales", "Meter Reading"]


def write(path, data):
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, "w", encoding="utf-8") as fh:
		json.dump(data, fh, indent=1, ensure_ascii=False)
		fh.write("\n")


def slug(n):
	return n.lower().replace(" ", "_").replace("-", "_")


def write_cards():
	for label, dt, flt, fn, _f in CARDS:
		write(os.path.join(BASE, "malls", "number_card", slug(label), slug(label) + ".json"), {
			"creation": TS, "docstatus": 0, "doctype": "Number Card", "document_type": dt, "filters_json": json.dumps(flt), "function": fn,
			"idx": 0, "is_public": 1, "is_standard": 1, "label": label, "modified": TS, "modified_by": "Administrator", "module": "Malls",
			"name": label, "owner": "Administrator", "show_percentage_stats": 0, "stats_time_interval": "Daily", "type": "Document Type"})
	for name, dt, typ, kind, x in CHARTS:
		d = {"chart_name": name, "creation": TS, "docstatus": 0, "doctype": "Dashboard Chart", "document_type": dt, "dynamic_filters_json": "",
			"idx": 0, "is_public": 1, "is_standard": 1, "modified": TS, "modified_by": "Administrator", "module": "Malls", "name": name,
			"number_of_groups": 0, "owner": "Administrator", "type": typ, "use_report_chart": 0, "y_axis": []}
		if kind == "group":
			d.update({"chart_type": "Group By", "group_by_based_on": x["by"], "group_by_type": "Count", "filters_json": json.dumps(x.get("filters", [])), "timeseries": 0})
		else:
			d.update({"chart_type": "Count", "based_on": x["based_on"], "filters_json": json.dumps(x["filters"]), "time_interval": x.get("interval", "Monthly"),
				"timeseries": 1, "timespan": x.get("timespan", "Last Year")})
		write(os.path.join(BASE, "malls", "dashboard_chart", slug(name), slug(name) + ".json"), d)


def main():
	write_cards()
	rid = lambda: uuid.uuid4().hex[:10]
	content = [{"id": rid(), "type": "header", "data": {"text": '<span class="h4"><b>Malls</b></span>', "col": 12}}]
	for label, *_r in CARDS:
		content.append({"id": rid(), "type": "number_card", "data": {"number_card_name": label, "col": 3}})
	for name, *_r in CHARTS:
		content.append({"id": rid(), "type": "chart", "data": {"chart_name": name, "col": 6}})
	shortcuts, links = [], []
	for label in TOP:
		content.insert(1 + len(shortcuts), {"id": rid(), "type": "shortcut", "data": {"shortcut_name": label, "col": 3}})
		kind = "DocType"
		sc = {"label": label, "link_to": label, "type": kind}
		if kind == "DocType":
			sc["doc_view"] = "List"
		else:
			sc["is_query_report"] = 1
		shortcuts.append(sc)
	for title, _i, _c, items in GROUPS:
		content.append({"id": rid(), "type": "card", "data": {"card_name": title, "col": 4}})
		links.append({"type": "Card Break", "label": title, "hidden": 0, "is_query_report": 0, "link_count": len(items), "onboard": 0})
		for label, kind, target, _icon in items:
			links.append({"type": "Link", "label": label, "link_type": kind, "link_to": target, "hidden": 0, "is_query_report": 1 if kind == "Report" else 0,
				"onboard": 0, "dependencies": "", "only_for": ""})
	write(os.path.join(BASE, "malls", "workspace", "malls", "malls.json"), {
		"charts": [{"chart_name": c[0], "label": c[0]} for c in CHARTS], "content": json.dumps(content), "creation": TS, "custom_blocks": [], "docstatus": 0, "doctype": "Workspace",
		"for_user": "", "hide_custom": 1, "icon": "building", "idx": 1, "is_hidden": 0, "label": "Malls", "links": links, "title": "Malls", "modified": TS,
		"modified_by": "Administrator", "module": "Malls", "name": "Malls", "number_cards": [{"label": c[0], "number_card_name": c[0]} for c in CARDS], "owner": "Administrator",
		"parent_page": "", "public": 1, "quick_lists": [], "roles": [], "sequence_id": 32.0, "shortcuts": shortcuts})
	def row(i, label, kind, target, icon, child):
		d = {"child": child, "collapsible": 1, "doctype": "Sidebar Item", "icon": icon, "idx": i, "indent": 0, "keep_closed": 0, "label": label,
			"parentfield": "items", "parenttype": "Sidebar", "show_arrow": 0, "type": "Link"}
		if kind == "URL":
			d.update({"link_type": "URL", "url": target, "open_in_new_tab": 1})
		else:
			d.update({"link_to": target, "link_type": kind})
		return d
	items = [row(1, "Home", "Workspace", "Malls", "house", 0)]
	for title, icon, closed, entries in GROUPS:
		if icon:
			items.append({"child": 0, "collapsible": 1, "doctype": "Sidebar Item", "icon": icon, "idx": len(items) + 1, "indent": 1, "keep_closed": closed,
				"label": title, "link_type": "DocType", "parentfield": "items", "parenttype": "Sidebar", "show_arrow": 0, "type": "Section Break"})
		for label, kind, target, ic in entries:
			items.append(row(len(items) + 1, label, kind, target, ic, 1 if icon else 0))
	write(os.path.join(BASE, "sidebar", "malls", "malls.json"), {"app": "ledgerx_malls", "doctype": "Sidebar", "header_icon": "building",
		"items": items, "module": "Malls", "name": "Malls", "standard": 1, "title": "Malls"})
	write(os.path.join(BASE, "dock", "malls", "malls.json"), {"app": "ledgerx_malls", "creation": TS, "docstatus": 0, "doctype": "Dock", "idx": 0,
		"items": [{"added": 0, "hidden": 0, "icon": "building", "link_to": "Malls", "link_type": "Sidebar", "title": "Malls"}],
		"modified": TS, "modified_by": "Administrator", "name": "malls", "owner": "Administrator", "standard": 1})


main()
