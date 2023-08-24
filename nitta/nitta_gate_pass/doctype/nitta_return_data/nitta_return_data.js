// Copyright (c) 2023, Ideenkreise and contributors
// For license information, please see license.txt

frappe.ui.form.on('Nitta Return Data', {
	refresh: function(frm) {
		// Check if the date field is empty before setting the current date
        if (!frm.doc.from_date) {
            var currentDate = frappe.datetime.get_today();
            frm.set_value('from_date', currentDate);
        }
		if (!frm.is_new() && (frm.doc.status == "Draft")  ) {
				
			cur_frm.page.add_action_item('Initiate', function () {
				frm.doc.status = "Initiated"
				frm.refresh_field("status")
				frm.dirty()
				frm.save()
			})
			frm.change_custom_button_type("Initiate", null, "primary");

		}

		if ((frm.doc.status !== "Draft") ) {
			frm.disable_save();
			frm.disable_form();
		}
		
		if (frm.doc.next_approved_by == frappe.session.user) {
			frm.page.add_action_item('Approve', () => {
				
				
				
					let index = frm.doc.workflow.findIndex((el) => el.employee == frappe.session.user && el.status != 'Approved')
					frm.doc.workflow[index].status = 'Approved'
					frm.refresh_field("workflow")
					frm.dirty()
					frm.save()
				
				
			})
			
		}

		frm.set_query('gate_pass', function () {
			return {
				query: "nitta.nitta_gate_pass.doctype.nitta_return_data.nitta_return_data.get_gate_pass",
				filters: { 'status': ['Final Approved', 'Partially Completed'] }
				
			};
		});
		

	},
	gate_pass:function(frm){
		frappe.call({
			method: "nitta.nitta_gate_pass.doctype.nitta_return_data.nitta_return_data.get_gatepass_details",
			args: {
				'gate_pass': frm.doc.gate_pass
			},
			callback: function (r) {
				
				r.message.forEach(el => {
					let found = false
					if (frm.doc.product) {
						found = frm.doc.product.find(function (record) {
							if (record.item == el.item)
								return true;
						});
					}

					if (!found) {
						frm.add_child('product', {
							item: el.item,
							work_to_be_done: el.work_to_be_done,
							quantity:el.quantity
							
						})

						frm.refresh_field('product')
					}
				});
		
			}
		});
	}
});
