// Copyright (c) 2023, Ideenkreise and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Nitta Delayed Gate Pass Report"] = {
	"filters": [
		{
			"fieldname": "division",
			"label": __("Division"),
			"fieldtype": "Link",
			"options": "Division",
			"reqd": 1,
			
			default:"All"


		}, {
			"fieldname": "department",
			"label": __("Department"),
			"fieldtype": "Link",
			"options": "Department",
			"reqd": 1,
			default: 'All'


		},
		

	]
};
