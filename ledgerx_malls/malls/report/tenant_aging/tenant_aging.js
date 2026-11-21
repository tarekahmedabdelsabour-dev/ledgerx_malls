frappe.query_reports["Tenant Aging"] = {
	filters: [
		{ fieldname: "mall", label: __("Mall"), fieldtype: "Link", options: "Mall" },
		{ fieldname: "as_of", label: __("As of"), fieldtype: "Date", default: frappe.datetime.get_today() },
	],
};
