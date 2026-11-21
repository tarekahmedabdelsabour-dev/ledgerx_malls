frappe.query_reports["Occupancy"] = {
	filters: [
		{ fieldname: "mall", label: __("Mall"), fieldtype: "Link", options: "Mall" },
		{ fieldname: "group_by", label: __("Group By"), fieldtype: "Select", options: ["", "Floor", "Category"], default: "Floor" },
	],
};
