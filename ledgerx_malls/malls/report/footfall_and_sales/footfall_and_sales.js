frappe.query_reports["Footfall and Sales"] = {
	filters: [
		{ fieldname: "mall", label: __("Mall"), fieldtype: "Link", options: "Mall" },
		{ fieldname: "from_month", label: __("From Month"), fieldtype: "Date", default: frappe.datetime.add_months(frappe.datetime.month_start(), -5), reqd: 1 },
		{ fieldname: "to_month", label: __("To Month"), fieldtype: "Date", default: frappe.datetime.month_start(), reqd: 1 },
	],
};
