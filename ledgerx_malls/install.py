"""Install and migrate steps. Each is idempotent and a failing step never aborts a migrate."""
import os

import frappe

MODULE, FOLDER = "Malls", "malls"
ROLES = ["Mall Manager", "Leasing Officer", "Mall Accountant", "Mall Operations"]
CATEGORIES = ["Fashion", "Food and Beverage", "Electronics", "Supermarket", "Entertainment", "Services", "Health and Beauty", "Home and Furniture", "Kiosk", "Anchor Store", "Other"]
ITEMS = {  # settings field -> (item code, name)
	"rent_item": ("MALL-RENT", "Mall Rent"), "service_item": ("MALL-SERVICE", "Mall Service Charge"), "marketing_item": ("MALL-MARKETING", "Mall Marketing Fund"),
	"utility_item": ("MALL-UTILITY", "Mall Utilities"), "turnover_item": ("MALL-TURNOVER", "Mall Turnover Rent"), "cam_item": ("MALL-CAM", "Mall Expense Recovery"),
	"late_fee_item": ("MALL-LATEFEE", "Mall Late Fee"),
}
FIELDS = [
	("Sales Invoice", "ml_section", {"label": "Mall", "fieldtype": "Section Break", "insert_after": "more_info", "collapsible": 1}),
	("Sales Invoice", "ml_mall", {"label": "Mall", "fieldtype": "Link", "options": "Mall", "insert_after": "ml_section", "in_standard_filter": 1, "read_only": 1}),
	("Sales Invoice", "ml_lease", {"label": "Mall Lease", "fieldtype": "Link", "options": "Mall Lease", "insert_after": "ml_mall", "read_only": 1, "in_standard_filter": 1}),
	("Sales Invoice", "ml_col", {"fieldtype": "Column Break", "insert_after": "ml_lease"}),
	("Sales Invoice", "ml_period", {"label": "Billing Month", "fieldtype": "Date", "insert_after": "ml_col", "read_only": 1}),
	("Sales Invoice", "ml_late_fee_until", {"label": "Late Fee Charged Until", "fieldtype": "Date", "insert_after": "ml_period", "read_only": 1}),
	("Sales Invoice Item", "ml_source", {"label": "Mall Source", "fieldtype": "Data", "insert_after": "description", "read_only": 1, "hidden": 1}),
	("Sales Invoice Item", "ml_through", {"label": "Mall Charged Through", "fieldtype": "Date", "insert_after": "ml_source", "read_only": 1, "hidden": 1}),
]


def check_app_permission():
	if frappe.session.user == "Administrator":
		return True
	return bool(set(frappe.get_roles()) & set(ROLES + ["System Manager", "Accounts Manager", "Accounts User"]))


def after_install():
	_all()


def after_migrate():
	_all()


def _all():
	for fn in (ensure_module, ensure_roles, ensure_custom_fields, ensure_categories, ensure_items, ensure_settings, refresh_workspace):
		try:
			fn()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title=f"ledgerx_malls install step failed: {fn.__name__}")
	frappe.clear_cache()


def ensure_module():
	if not frappe.db.exists("Module Def", MODULE):
		frappe.get_doc({"doctype": "Module Def", "module_name": MODULE, "app_name": "ledgerx_malls"}).insert(ignore_permissions=True)


def ensure_roles():
	for r in ROLES:
		if not frappe.db.exists("Role", r):
			frappe.get_doc({"doctype": "Role", "role_name": r, "desk_access": 1}).insert(ignore_permissions=True)


def ensure_custom_fields():
	for dt, name, spec in FIELDS:
		if frappe.db.exists("DocType", dt) and not frappe.db.exists("Custom Field", {"dt": dt, "fieldname": name}):
			frappe.get_doc({"doctype": "Custom Field", "dt": dt, "fieldname": name, **spec}).insert(ignore_permissions=True)


def ensure_categories():
	for c in CATEGORIES:
		if not frappe.db.exists("Mall Category", c):
			frappe.get_doc({"doctype": "Mall Category", "category_name": c}).insert(ignore_permissions=True)


def ensure_items():
	group = "Services" if frappe.db.exists("Item Group", "Services") else frappe.db.get_value("Item Group", {"is_group": 0}, "name")
	uom = "Nos" if frappe.db.exists("UOM", "Nos") else frappe.db.get_value("UOM", {}, "name")
	if not (group and uom):
		return
	for code, name in ITEMS.values():
		if not frappe.db.exists("Item", code):
			frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": name, "item_group": group, "stock_uom": uom, "is_stock_item": 0, "include_item_in_manufacturing": 0}).insert(ignore_permissions=True)


def ensure_settings():
	s = frappe.get_doc("Mall Settings")
	changed = False
	if not s.company:
		s.company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value("Company", {}, "name")
		changed = bool(s.company)
	for fld, (code, _n) in ITEMS.items():
		if not s.get(fld) and frappe.db.exists("Item", code):
			s.set(fld, code)
			changed = True
	if changed and s.company:
		s.save(ignore_permissions=True)


def refresh_workspace():
	base = os.path.join(frappe.get_app_path("ledgerx_malls"), FOLDER)
	for dt in ("number_card", "dashboard_chart"):
		folder = os.path.join(base, dt)
		for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
			if os.path.isdir(os.path.join(folder, name)):
				frappe.reload_doc(FOLDER, dt, name, force=True)
	frappe.reload_doc(FOLDER, "workspace", "malls", force=True)
