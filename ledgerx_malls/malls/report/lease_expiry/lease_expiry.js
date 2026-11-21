frappe.query_reports["Lease Expiry"] = {
	filters: [
		{ fieldname: "mall", label: __("Mall"), fieldtype: "Link", options: "Mall" },
		{ fieldname: "within_days", label: __("Ending Within (days)"), fieldtype: "Int", default: 365 },
	],
};
