frappe.query_reports["Rent Roll"] = {
	filters: [
		{ fieldname: "mall", label: __("Mall"), fieldtype: "Link", options: "Mall" },
		{ fieldname: "include_ended", label: __("Include Expired and Terminated"), fieldtype: "Check" },
	],
};
