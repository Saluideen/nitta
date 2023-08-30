// Copyright (c) 2023, Ideenkreise and contributors
// For license information, please see license.txt
// Declare department_store globally

frappe.ui.form.on('Nitta Return Data', {
	refresh: function(frm) {

		frappe.call({
			method: "nitta.nitta_gate_pass.doctype.nitta_return_data.nitta_return_data.get_employee_details",
			async: false,
			args: {
				'name': frappe.session.user
			},
			callback: function (r) {
				console.log("r.message[0].department",r.message[0].department);
				frm.set_value('department_store', r.message[0].department);
				
				
			
			}
		});
		
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

		if ((frm.doc.status !== "Draft") && (frm.doc.department_store !="Store") ) {
			frm.disable_save();
			frm.disable_form();
			
		}
		if ((frm.doc.status == "Final Approved") && (frm.doc.department_store =="Store") ) {
			frm.disable_save();
			frm.disable_form();
			
		}
		if(frm.doc.department_store=="Store"){
			
			frm.set_df_property("item_state", "hidden", 0);
			frm.set_df_property("from_date", "read_only", 1);
			frm.set_df_property("vendor_name", "read_only", 1);
			frm.set_df_property("workflow", "read_only", 1);
			frm.set_df_property("product", "read_only", 1);
		}
		
		if ((frm.doc.next_approved_by == frappe.session.user)) {
			// if((frm.doc.status !="Final Approved")){
				frm.page.add_action_item('Approve', () => {
				
				
				
					let index = frm.doc.workflow.findIndex((el) => el.employee == frappe.session.user && el.status != 'Approved')
					frm.doc.workflow[index].status = 'Approved'
					frm.refresh_field("workflow")
					frm.dirty()
					frm.save()
				
				
			})

			// }
			
			
		}

		frm.set_query('gate_pass', function () {
			return {
				// query: "nitta.nitta_gate_pass.doctype.nitta_return_data.nitta_return_data.get_gate_pass",
				filters: { 'status':['in', ['Final Approved', 'Not Completed']] }
				
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
				console.log(r.message[1]);
				
				r.message[0].forEach(el => {
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
							quantity:el.quantity,
							remaining_quantity:el.remaining_quantity,
							remarks:el.remarks,
							previous_return_quantity:el.return_quantity,
							expected_delivery_date:el.expected_delivery_date
							
						})

						frm.refresh_field('product')
					}
				});
				r.message[1].forEach(el =>{
					
					frm.set_value('department', el.department);
				frm.set_value("division",el.division)

				})
		
			}
		});
	}
});
frappe.ui.form.on('Return product Details', {
   

    return_quantity: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];
		let remains=row.return_quantity+row.previous_return_quantity;
        let remaining_quantity = row.quantity-remains
        frappe.model.set_value(cdt, cdn, 'remaining_quantity', remaining_quantity);
    }
});