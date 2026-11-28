"""Demo data for the Malls app: one mall per country (Egypt, Saudi Arabia, UAE) with floors, units, tenants, leases (fixed, percentage of sales and
higher-of, with escalation, service charge, marketing fund, a rent-free fit-out), utility meters and readings, monthly tenant sales, footfall,
a CAM allocation and a billing run for last month that is prepared and invoiced through the app's own methods.

    bench --site mysite.localhost execute ledgerx_malls.demo.run

Run ledgerx.demo.foundation first (companies, cost centers, customer group). Take a backup first.
Idempotent: every record is looked up by its natural key before it is created. Every step commits on its own and reports its result;
failures are logged in Error Log under titles starting 'Demo malls'. Run as Administrator (bench execute does: tenant sales are marked Verified).
Invoices of the billing run are left as drafts (the run's Submit Invoices button is the next click of the demo). Mall Settings is filled only where empty.
"""
import frappe
from frappe.utils import add_days, flt, getdate, nowdate

from ledgerx.shared import run_each
from ledgerx_malls.engine.billing import add_months, month_end, month_start

# unit no, floor, category, area sqm, list-rent factor, anchor, status when no lease
UNITS = [
	("G-01", "Ground", "Fashion", 120, 1.0, 0, "Vacant"),
	("G-02", "Ground", "Fashion", 80, 1.0, 0, "Vacant"),
	("G-03", "Ground", "Electronics", 95, 1.0, 0, "Vacant"),
	("G-04", "Ground", "Food and Beverage", 60, 1.3, 0, "Vacant"),
	("G-05", "Ground", "Supermarket", 600, 0.4, 1, "Vacant"),
	("F-01", "First", "Entertainment", 350, 0.5, 0, "Vacant"),
	("F-02", "First", "Health and Beauty", 70, 0.8, 0, "Vacant"),
	("F-03", "First", "Services", 50, 0.8, 0, "Vacant"),
	("F-04", "First", "Home and Furniture", 110, 0.7, 0, "Maintenance"),
]
# lease: tenant index, units, rent model, rent factor, rent escalation %, turnover %, service factor, service escalation %, marketing %, started days ago, years, free-from (days from today), free-to
F, P, H = "Fixed", "Percentage of Sales", "Higher of Fixed and Percentage"
LEASES = [
	(0, ["G-01"], F, 1.0, 5, 0, 1.0, 3, 2, 430, 3, None),
	(1, ["G-02"], H, 0.8, 5, 8, 1.0, 3, 2, 400, 3, None),
	(2, ["G-03"], P, 0, 0, 7, 1.0, 3, 0, 380, 3, None),
	(3, ["G-04"], H, 1.0, 7, 10, 1.2, 3, 3, 600, 2, None),
	(4, ["G-05"], F, 1.0, 4, 0, 0.6, 3, 0, 700, 10, None),
	(5, ["F-01"], F, 1.0, 5, 0, 0.8, 3, 1, 365, 5, None),
	(6, ["F-02"], P, 0, 0, 12, 1.0, 3, 0, 300, 3, None),
	(7, ["F-03"], F, 1.0, 5, 0, 1.0, 3, 2, 27, 3, (-27, 17)),  # signed this month, rent-free fit-out (Egypt only)
]

# mall key: name, company, cost center, territory, city, address, opened, manager designation, per-sqm rates (rent, service, CAM, sales), meter rates (electricity, water), customer-name country tag
MALLS = {
	"eg": dict(name="Nile Gate Mall", company="LedgerX Egypt", cc="Cairo - LXE", territory="Egypt", city="Cairo", address="Ring Road, New Cairo, Cairo", opened="2016-03-01",
		rent=1200, svc=150, cam=120, sales=10000, kwh=2.2, water=14, leases=8,
		tenants=[("Nefertiti Fashion Trading", "Nefertiti Fashion", "Fashion", "Mona Abdel Aziz"), ("Delta Kids Wear", "Delta Kids", "Fashion", "Sherif Hassan"),
			("El Sherif Electronics", "El Sherif Electronics", "Electronics", "Tarek El Sherif"), ("Abou Tarek Food Services", "Abou Tarek Koshary", "Food and Beverage", "Hany Abou Tarek"),
			("Hyper Masr Supermarkets", "Hyper Masr", "Supermarket", "Ayman Fouad"), ("Layali Entertainment", "Layali Fun City", "Entertainment", "Dina Kamel"),
			("Cleopatra Beauty Centers", "Cleopatra Beauty", "Health and Beauty", "Heba Saleh"), ("Sahel Mobile Services", "Sahel Mobile", "Services", "Khaled Mansour")]),
	"sa": dict(name="Najd Plaza Mall", company="LedgerX Saudi", cc="Riyadh - LXS", territory="Saudi Arabia", city="Riyadh", address="King Fahd Road, Al Olaya, Riyadh", opened="2018-09-15",
		rent=160, svc=20, cam=16, sales=1400, kwh=0.3, water=9, leases=7,
		tenants=[("Najd Fashion Trading Co", "Najd Fashion", "Fashion", "Faisal Al-Otaibi"), ("Dar Al Oud Perfumes", "Dar Al Oud", "Fashion", "Abdullah Al-Qahtani"),
			("Souq Al Electronics", "Souq Electronics", "Electronics", "Salman Al-Harbi"), ("Bayt Al Qahwa Cafes", "Bayt Al Qahwa", "Food and Beverage", "Noura Al-Shammari"),
			("Al Hala Supermarkets", "Al Hala Market", "Supermarket", "Fahad Al-Mutairi"), ("Riyadh Fun Zone Co", "Fun Zone", "Entertainment", "Reem Al-Ghamdi"),
			("Safa Beauty Clinics", "Safa Beauty", "Health and Beauty", "Lama Al-Dosari")]),
	"ae": dict(name="Marina Walk Mall", company="LedgerX UAE", cc="Dubai - LXA", territory="United Arab Emirates", city="Dubai", address="Sheikh Zayed Road, Dubai Marina, Dubai", opened="2019-11-01",
		rent=180, svc=22, cam=18, sales=1600, kwh=0.38, water=10, leases=7,
		tenants=[("Marina Threads Trading LLC", "Marina Threads", "Fashion", "Hamad Al-Mazrouei"), ("Emirates Gold and Jewels LLC", "Emirates Gold", "Fashion", "Rashid Al-Falasi"),
			("Gadget Oasis LLC", "Gadget Oasis", "Electronics", "Saeed Al-Nuaimi"), ("Karak Corner Cafe LLC", "Karak Corner", "Food and Beverage", "Mariam Al-Suwaidi"),
			("Al Dhafra Fresh Market LLC", "Al Dhafra Fresh", "Supermarket", "Majid Al-Ketbi"), ("Splash Kids Play LLC", "Splash Play", "Entertainment", "Latifa Al-Zaabi"),
			("Pearl Wellness Spa LLC", "Pearl Wellness", "Health and Beauty", "Aisha Al-Hammadi")]),
}
SALES_FACTOR = [1.0, 1.1, 0.9, 1.2, 1.0, 0.8, 1.15, 1.0]
SALES_MONTHS_BACK = (4, 3, 2, 1)  # months before this one; the run bills last month on the sales of the month before it
UNVERIFIED = (1, 3)  # tenant indexes whose sales of two months back stay Declared, so the run shows a turnover rent left unticked


def _say(msg):
	print(msg)


def _insert(doc):
	return frappe.get_doc(doc).insert(ignore_permissions=True)


def _mall(key):
	return MALLS[key]["name"]


def _unit_name(key, no):
	return f"{_mall(key)}-{no}"


def _lease_rows(key):
	return LEASES[: MALLS[key]["leases"]]


def _last_month():
	return month_start(add_months(getdate(nowdate()), -1))


# ------------------------------------------------------------------ masters
def _settings(_x):
	"""Fill Mall Settings only where empty (items are filled by the app's install)."""
	s = frappe.get_doc("Mall Settings")
	if not s.company and frappe.db.exists("Company", "LedgerX Egypt"):
		frappe.db.set_single_value("Mall Settings", "company", "LedgerX Egypt")
	for fld, code in (("rent_item", "MALL-RENT"), ("service_item", "MALL-SERVICE"), ("marketing_item", "MALL-MARKETING"), ("utility_item", "MALL-UTILITY"),
		("turnover_item", "MALL-TURNOVER"), ("cam_item", "MALL-CAM"), ("late_fee_item", "MALL-LATEFEE")):
		if not s.get(fld) and frappe.db.exists("Item", code):
			frappe.db.set_single_value("Mall Settings", fld, code)
	frappe.clear_document_cache("Mall Settings", "Mall Settings")


def _category(name):
	if not frappe.db.exists("Mall Category", name):
		_insert({"doctype": "Mall Category", "category_name": name})


def _mall_doc(key):
	m = MALLS[key]
	if frappe.db.exists("Mall", m["name"]):
		return
	if not frappe.db.exists("Company", m["company"]):
		frappe.throw(f"Company {m['company']} is missing. Run ledgerx.demo.foundation first.")
	manager = frappe.db.get_value("Employee", {"company": m["company"], "status": "Active", "designation": "Branch Manager"}, "name")
	_insert({"doctype": "Mall", "mall_name": m["name"], "company": m["company"], "active": 1, "cost_center": m["cc"] if frappe.db.exists("Cost Center", m["cc"]) else None,
		"manager": manager, "city": m["city"], "address": m["address"], "opening_date": m["opened"]})


def _floors(key):
	for i, fl in enumerate(("Ground", "First")):
		if not frappe.db.exists("Mall Floor", f"{_mall(key)}-{fl}"):
			_insert({"doctype": "Mall Floor", "mall": _mall(key), "floor_name": fl, "level": i})


def _units(key):
	m = MALLS[key]
	for no, floor, cat, area, f, anchor, status in UNITS:
		if frappe.db.exists("Mall Unit", _unit_name(key, no)):
			continue
		_insert({"doctype": "Mall Unit", "unit_no": no, "mall": m["name"], "floor": f"{m['name']}-{floor}", "category": cat, "area_sqm": area, "list_rent_sqm": round(m["rent"] * f),
			"is_anchor": anchor, "active": 1, "status": status})


def _group():
	return "Commercial" if frappe.db.exists("Customer Group", "Commercial") else frappe.db.get_value("Customer Group", {"is_group": 0}, "name")


def _tenants(key):
	m = MALLS[key]
	for i, (legal, trade, cat, contact) in enumerate(m["tenants"]):
		if frappe.db.exists("Mall Tenant", {"tenant_name": legal}):
			continue
		cust = frappe.db.get_value("Customer", {"customer_name": legal}, "name")
		if not cust:
			cust = _insert({"doctype": "Customer", "customer_name": legal, "customer_type": "Company", "customer_group": _group(),
				"territory": m["territory"] if frappe.db.exists("Territory", m["territory"]) else frappe.db.get_value("Territory", {"is_group": 0}, "name")}).name
		slug = "".join(ch for ch in trade.lower() if ch.isalnum())
		_insert({"doctype": "Mall Tenant", "tenant_name": legal, "trade_name": trade, "customer": cust, "category": cat, "status": "Active",
			"commercial_register": f"CR-{key.upper()}-{4100 + i * 37}", "tax_id": f"{key.upper()}-TX-{300100 + i * 211}", "contact_person": contact,
			"phone": {"eg": "+20 10 0555 ", "sa": "+966 50 555 ", "ae": "+971 50 555 "}[key] + f"{1200 + i * 111}", "email": f"leasing@{slug}.example.com"})


def _lease(key_idx):
	key, idx = key_idx.split(":")
	idx = int(idx)
	m = MALLS[key]
	t, units, model, rf, resc, tpct, sf, sesc, mkt, ago, years, free = _lease_rows(key)[idx]
	legal = m["tenants"][t][0]
	tenant = frappe.db.get_value("Mall Tenant", {"tenant_name": legal}, "name")
	if not tenant:
		frappe.throw(f"Tenant {legal} is missing")
	first_unit = _unit_name(key, units[0])
	if frappe.db.sql("""select l.name from `tabMall Lease` l join `tabLease Unit` u on u.parent = l.name
			where l.mall = %s and l.tenant = %s and u.unit = %s and l.docstatus = 1 limit 1""", (m["name"], tenant, first_unit)):
		return
	start = add_days(nowdate(), -ago)
	area = sum(u[3] for u in UNITS if u[0] in units)
	base_unit = {u[0]: u[4] for u in UNITS}[units[0]]
	rent = round(m["rent"] * base_unit * rf) if model != P else 0
	doc = {"doctype": "Mall Lease", "mall": m["name"], "tenant": tenant, "start_date": start, "end_date": add_days(frappe.utils.add_years(start, years), -1),
		"units": [{"unit": _unit_name(key, u)} for u in units], "rent_model": model, "rent_basis": "Per sqm per Month", "rent_amount": rent, "rent_escalation_pct": resc,
		"turnover_pct": tpct, "service_per_sqm": round(m["svc"] * sf, 2), "service_escalation_pct": sesc, "marketing_pct": mkt, "recover_cam": 1,
		"security_deposit": round(rent * area * 3) if rent else round(m["rent"] * area), "deposit_status": "Received"}
	if free:
		doc["free_periods"] = [{"from_date": add_days(nowdate(), free[0]), "to_date": add_days(nowdate(), free[1]), "applies_to": "All", "note": "Fit-out period"}]
		doc["deposit_status"] = "Pending"
	_insert(doc).submit()


def _meters(key):
	m = MALLS[key]
	for idx, row in enumerate(_lease_rows(key)):
		if row[11]:
			continue  # fit-out unit has no consumption yet
		unit = row[1][0]
		area = sum(u[3] for u in UNITS if u[0] == unit)
		specs = [("EL-" + unit, "Electricity", m["kwh"], 12000 + idx * 800)]
		if unit == "G-04":
			specs.append(("WT-" + unit, "Water", m["water"], 300))
		if unit == "G-05":
			specs.append(("AC-" + unit, "Air Conditioning", round(m["kwh"] * 1.4, 2), 5000))
		for no, util, rate, opening in specs:
			name = f"{m['name']}-{no}"
			if not frappe.db.exists("Utility Meter", name):
				_insert({"doctype": "Utility Meter", "meter_no": no, "mall": m["name"], "unit": _unit_name(key, unit), "utility": util, "multiplier": 1, "rate": rate,
					"opening_reading": opening, "active": 1})


def _readings(key):
	"""One reading per meter at the end of last month (consumption since the opening reading); the billing run charges it."""
	m = MALLS[key]
	on = month_end(_last_month())
	for meter in frappe.get_all("Utility Meter", filters={"mall": m["name"]}, fields=["name", "unit", "utility", "opening_reading"]):
		if frappe.db.exists("Meter Reading", {"meter": meter.name, "reading_date": on}):
			continue
		area = frappe.db.get_value("Mall Unit", meter.unit, "area_sqm")
		per_sqm = {"Electricity": 38, "Water": 4, "Air Conditioning": 20}.get(meter.utility, 10)
		_insert({"doctype": "Meter Reading", "meter": meter.name, "reading_date": on, "reading": flt(meter.opening_reading) + round(area * per_sqm)})


def _sales(key):
	m = MALLS[key]
	today = getdate(nowdate())
	for idx, row in enumerate(_lease_rows(key)):
		if row[11]:
			continue
		lease = frappe.db.sql("""select l.name, l.total_area from `tabMall Lease` l join `tabLease Unit` u on u.parent = l.name
			where l.mall = %s and u.unit = %s and l.docstatus = 1 limit 1""", (m["name"], _unit_name(key, row[1][0])), as_dict=True)
		if not lease:
			continue
		for back in SALES_MONTHS_BACK:
			month = month_start(add_months(today, -back))
			if frappe.db.exists("Tenant Sales", {"lease": lease[0].name, "month": month}):
				continue
			wiggle = 1 + ((back * 7 + idx * 3) % 9 - 4) / 40.0
			gross = round(flt(lease[0].total_area) * m["sales"] * SALES_FACTOR[idx] * wiggle, -2)
			declared = back == 2 and idx in UNVERIFIED
			_insert({"doctype": "Tenant Sales", "lease": lease[0].name, "month": month, "gross_sales": gross, "returns": round(gross * 0.03, -1),
				"status": "Declared" if declared or back == 1 else "Verified", "evidence": "POS Z-report submitted by the tenant" if not declared else "Awaiting POS report"})


def _footfall(key):
	m = MALLS[key]
	for back in range(1, 15):
		day = add_days(nowdate(), -back)
		if frappe.db.exists("Footfall", {"mall": m["name"], "date": day, "entrance": "Main"}):
			continue
		weekend = getdate(day).weekday() in (4, 5)
		_insert({"doctype": "Footfall", "mall": m["name"], "date": day, "entrance": "Main", "visitors": int((9000 if weekend else 6200) + (back * 137) % 900)})


def _cam(key):
	m = MALLS[key]
	today = getdate(nowdate())
	first, last = month_start(add_months(today, -4)), month_end(add_months(today, -2))
	if frappe.db.exists("CAM Allocation", {"mall": m["name"], "from_date": first, "to_date": last}):
		return
	gla = sum(u[3] for u in UNITS)
	doc = _insert({"doctype": "CAM Allocation", "mall": m["name"], "from_date": first, "to_date": last, "total_expense": round(gla * m["cam"] * 3, -3), "landlord_bears_vacant": 1})
	doc.allocate()


def _billing(key):
	"""Billing run for last month, prepared then invoiced with the app's own methods (draft invoices)."""
	m = MALLS[key]
	month = _last_month()
	name = frappe.db.get_value("Mall Billing Run", {"mall": m["name"], "billing_month": month}, "name")
	run = frappe.get_doc("Mall Billing Run", name) if name else _insert({"doctype": "Mall Billing Run", "mall": m["name"], "billing_month": month, "posting_date": nowdate(),
		"bill_turnover": 1, "bill_utilities": 1, "bill_cam": 1, "bill_late_fees": 1})
	if run.status == "Invoiced":
		return
	if run.status != "Prepared":
		run.prepare()
	run.create_invoices()


STEPS = [
	("Settings", _settings, [1]),
	("Categories", _category, ["Fashion", "Food and Beverage", "Electronics", "Supermarket", "Entertainment", "Services", "Health and Beauty", "Home and Furniture"]),
	("Malls", _mall_doc, list(MALLS)),
	("Floors", _floors, list(MALLS)),
	("Units", _units, list(MALLS)),
	("Tenants", _tenants, list(MALLS)),
	("Leases", _lease, [f"{k}:{i}" for k in MALLS for i in range(MALLS[k]["leases"])]),
	("Utility meters", _meters, list(MALLS)),
	("Meter readings", _readings, list(MALLS)),
	("Tenant sales", _sales, list(MALLS)),
	("Footfall", _footfall, list(MALLS)),
	("CAM allocations", _cam, list(MALLS)),
	("Billing runs", _billing, list(MALLS)),
]


def run():
	_say("Malls demo data")
	failed_any = False
	for label, fn, items in STEPS:
		done, failed = run_each(items, fn, f"Demo malls: {label}")
		failed_any = failed_any or bool(failed)
		_say(f"  {label}: {len(done)} ok, {len(failed)} failed")
	if failed_any:
		_say("Some steps failed. Open Error Log (titles start with 'Demo malls') and send me the errors.")
	else:
		_say("Done. Open the Malls workspace: occupancy, rent roll, lease expiry, tenant sales, and the billing runs with draft invoices are filled.")
