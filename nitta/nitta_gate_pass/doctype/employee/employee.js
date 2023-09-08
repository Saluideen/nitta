// Copyright (c) 2023, Ideenkreise and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee', {
	refresh: function(frm) {
		frm.fields_dict['roles'].grid.get_field('department').get_query = function (doc, cdt, cdn) {
			var child = locals[cdt][cdn];
		
			return {
				filters: [['name', 'not in', ['FROM GATEPASS']]]
			};
		}
		
}
});
