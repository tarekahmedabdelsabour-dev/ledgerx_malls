app_name = "ledgerx_malls"
app_title = "Malls"
app_publisher = "LedgerX"
app_description = "Shopping-mall management: units, tenants, leases with fixed and turnover rent, monthly billing, service charges, meters, tenant sales and footfall"
app_email = "hello@ledgerx.local"
app_license = "mit"

required_apps = ["erpnext"]

add_to_apps_screen = [
	{
		"name": "ledgerx_malls",
		"logo": "/assets/ledgerx_malls/images/malls.svg",
		"title": "Malls",
		"route": "/desk/malls",
		"has_permission": "ledgerx_malls.install.check_app_permission",
	}
]

doc_events = {
	"Sales Invoice": {"on_submit": "ledgerx_malls.invoices.on_submit", "on_cancel": "ledgerx_malls.invoices.on_cancel", "on_trash": "ledgerx_malls.invoices.on_trash"},
}

override_doctype_dashboards = {
	"Customer": "ledgerx_malls.overrides.customer",
	"Employee": "ledgerx_malls.overrides.employee",
}

scheduler_events = {
	"cron": {
		"15 5 * * *": ["ledgerx_malls.tasks.daily"],
	},
}

from ledgerx_malls import __version__ as _v  # noqa: E402

app_include_js = [f"/assets/ledgerx_malls/js/mall_forms.js?v={_v}"]

after_install = "ledgerx_malls.install.after_install"
after_migrate = "ledgerx_malls.install.after_migrate"
