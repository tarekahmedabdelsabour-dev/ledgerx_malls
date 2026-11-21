(function () {
	const call = (frm, method, args, then) =>
		frm.call({ doc: frm.doc, method, args, freeze: true }).then((r) => { if (then) then(r.message); frm.reload_doc(); });

	frappe.ui.form.on("Mall Lease", {
		setup(frm) {
			frm.set_query("unit", "units", () => ({ filters: { mall: frm.doc.mall, active: 1 } }));
			frm.set_query("tenant", () => ({ filters: { status: ["!=", "Former"] } }));
		},
		refresh(frm) {
			if (frm.doc.docstatus !== 1) return;
			if (!frm.doc.terminated_on && frm.doc.lease_status !== "Expired") {
				frm.add_custom_button(__("Terminate"), () =>
					frappe.prompt([
						{ fieldname: "date", label: __("Last Day of the Lease"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() },
						{ fieldname: "reason", label: __("Reason"), fieldtype: "Small Text" },
					], (v) => call(frm, "terminate", v), __("Terminate the Lease"), __("Terminate")), __("Actions"));
			}
			frm.add_custom_button(__("Renew"), () =>
				frappe.prompt([
					{ fieldname: "years", label: __("New Term (years)"), fieldtype: "Int", reqd: 1, default: 3 },
					{ fieldname: "rent_increase_pct", label: __("Rent Increase %"), fieldtype: "Percent", default: 10 },
				], (v) => frm.call({ doc: frm.doc, method: "renew", args: v, freeze: true }).then((r) => r.message && frappe.set_route("Form", "Mall Lease", r.message)), __("Renew the Lease"), __("Create Draft Renewal")), __("Actions"));
			frm.add_custom_button(__("Enter Sales"), () => frappe.new_doc("Tenant Sales", { lease: frm.doc.name }), __("Actions"));
		},
	});

	frappe.ui.form.on("Tenant Sales", {
		setup(frm) {
			frm.set_query("lease", () => ({ filters: { docstatus: 1, lease_status: ["in", ["Active", "Expired", "Terminated"]] } }));
		},
		gross_sales: (frm) => net(frm), returns: (frm) => net(frm),
	});
	function net(frm) { frm.set_value("net_sales", flt(frm.doc.gross_sales) - flt(frm.doc.returns)); }

	frappe.ui.form.on("CAM Allocation", {
		refresh(frm) {
			if (frm.is_new() || frm.doc.status === "Billed") return;
			frm.add_custom_button(__("Load Expenses"), () => call(frm, "load_expenses"), __("Allocation"));
			frm.add_custom_button(__("Allocate"), () => call(frm, "allocate", {}, (n) => frappe.show_alert({ message: __("{0} leases share the expenses", [n]), indicator: "green" })), __("Allocation")).addClass("btn-primary");
		},
	});

	frappe.ui.form.on("Mall Billing Run", {
		refresh(frm) {
			if (frm.is_new()) return;
			if (frm.doc.status !== "Invoiced") {
				frm.add_custom_button(__("Prepare Charges"), () => call(frm, "prepare", {}, (n) => frappe.show_alert({ message: __("{0} charge lines", [n]), indicator: "green" })), __("Run")).addClass(frm.doc.status === "Draft" ? "btn-primary" : "");
			}
			if (frm.doc.status === "Prepared") {
				frm.add_custom_button(__("Create Invoices"), () => frappe.confirm(__("Create one draft invoice per lease for the ticked lines?"), () => call(frm, "create_invoices")), __("Run")).addClass("btn-primary");
			}
			if (frm.doc.status === "Invoiced") {
				frm.add_custom_button(__("Submit Invoices"), () => frappe.confirm(__("Submit all the draft invoices of this run?"), () => call(frm, "submit_invoices", {}, (n) => frappe.show_alert({ message: __("{0} invoices submitted", [n]), indicator: "green" }))), __("Run")).addClass("btn-primary");
			}
		},
	});

	frappe.ui.form.on("Meter Reading", {
		setup(frm) { frm.set_query("meter", () => ({ filters: { active: 1 } })); },
	});

	frappe.ui.form.on("Mall", {
		refresh(frm) {
			if (frm.is_new()) return;
			frm.add_custom_button(__("Units"), () => frappe.set_route("List", "Mall Unit", { mall: frm.doc.name }), __("View"));
			frm.add_custom_button(__("Rent Roll"), () => frappe.set_route("query-report", "Rent Roll", { mall: frm.doc.name }), __("View"));
			frm.add_custom_button(__("New Billing Run"), () => frappe.new_doc("Mall Billing Run", { mall: frm.doc.name, billing_month: frappe.datetime.month_start() }), __("Create"));
			frm.add_custom_button(__("Expense Recovery"), () => frappe.new_doc("CAM Allocation", { mall: frm.doc.name }), __("Create"));
		},
	});
})();
