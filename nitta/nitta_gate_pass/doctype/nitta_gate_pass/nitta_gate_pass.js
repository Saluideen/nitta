// Copyright (c) 2023, Ideenkreise and contributors
// For license information, please see license.txt

frappe.ui.form.on("Nitta Gate Pass", {
  refresh: function (frm) {


    frappe.call({
			method: "nitta.nitta_gate_pass.doctype.nitta_return_data.nitta_return_data.get_employee_details",
			async: false,
			args: {
				'name': frappe.session.user
			},
			callback: function (r) {
				
				frm.set_value('current_department', r.message[0].department);
				
				
			
			}
		});

	$(".btn.btn-new.btn-secondary.btn-xs.icon-btn").hide();
    // Check if the date field is empty before setting the current date
    if (!frm.doc.from_date) {
      var currentDate = frappe.datetime.get_today();
      frm.set_value("from_date", currentDate);
    }

	if (roles.includes("Security")) {
		
		
		
		frm.set_df_property("way_of_dispatch","hidden",0);
		
	  }
    if(frm.is_new()){
       //set initiator  department nd division
    frappe.call({
      method:
        "nitta.nitta_gate_pass.doctype.nitta_gate_pass.nitta_gate_pass.get_employee_details",
      args: {
        name: frappe.user.name,
      },
      callback: function (r) {
        frm.doc.division = r.message[0].division;
        frm.doc.department = r.message[0].department;
        frm.doc.role = r.message[0].roles;
        frm.doc.user = r.message[0].user;
        frm.refresh_field("division");
        frm.refresh_field("department");
        frm.refresh_field("role");
        frm.refresh_field("user");
      },
    });
    frm.set_df_property("workflow_name", "hidden", 1);
    frm.set_df_property("workflow", "hidden", 1);
    frm.set_df_property("next_approved_by", "hidden", 1);
    frm.set_df_property("status", "hidden", 1);
   

    }
   
    // Initiate only creator.
    if (!frm.is_new() && frm.doc.status == "Draft" && roles.includes("User") ) {
      cur_frm.page.add_action_item("Initiate", function () {
        frm.doc.status = "Initiated";
        frm.refresh_field("status");
        frm.dirty();
        frm.save();
      });
      frm.change_custom_button_type("Initiate", null, "primary");
    }

	if ((frm.doc.status !== "Draft") && (!roles.includes("Security")) ) {
		frm.disable_save();
		frm.disable_form();
	}
    
	if ((frm.doc.status == "Dispatched") && (roles.includes("Security")) ) {
		frm.disable_save();
		frm.disable_form();
	}
  if ((frm.doc.status == "Close") && (roles.includes("Security")) ) {
		frm.disable_save();
		frm.disable_form();
	}
  if(roles.includes("Security")){
        frm.set_df_property("from_date","read_only", 1);
        frm.set_df_property("is_emergency","read_only", 1);
        frm.set_df_property("vendor","read_only", 1);
        frm.set_df_property("item","read_only", 1);
        frm.set_df_property("workflow","read_only", 1);

  }

    if ((frm.doc.next_approved_by == frappe.session.user) && (frm.doc.status !="Dispatched")&& (frm.doc.status !="Close") &&(frm.doc.status !="Not Completed")) {
      frm.page.add_action_item("Approve", () => {
        let index = frm.doc.workflow.findIndex(
          (el) => el.employee == frappe.session.user && el.status != "Approved"
        );
        frm.doc.workflow[index].status = "Approved";
        frm.refresh_field("workflow");
        frm.dirty();
        frm.save();
      });

      if ((frm.doc.status == "Initiated")&& (!(frm.doc.is_emergency))) {
        frm.page.add_action_item("Reject", () => {
          let index = frm.doc.workflow.findIndex(
            (el) =>
              el.employee == frappe.session.user && el.status != "Rejected"
          );
          frm.doc.workflow[index].status = "Rejected";
          frm.refresh_field("workflow");
          frm.dirty();
          frm.save();
        });
      }
    }
  },
  way_of_dispatch: function (frm) {
    frm.refresh();
    let way_of_dispatch = frm.doc.way_of_dispatch;
    if (way_of_dispatch == "By Hand") {
      frm.set_df_property("recipient", "hidden", 0);
      frm.set_df_property("phone", "hidden", 0);
    } else if (way_of_dispatch == "Vehicle") {
      frm.set_df_property("driver_name", "hidden", 0);
      frm.set_df_property("contact_number", "hidden", 0);
      frm.set_df_property("registration_number", "hidden", 0);
      frm.set_df_property("recipient", "hidden", 1);
      frm.set_df_property("phone", "hidden", 1);
    }
  },
  // workflow_type: function (frm) {
  //   console.log("workflow_type", frm.doc.workflow_type);
  //   if (frm.doc.workflow_type == "Arrival") {
  //     frm.set_df_property("quantity", "hidden", 0);
  //     frm.add_custom_button("Return", function () {
  //       frm.doc.status = "Return";
  //       frm.refresh_field("status");
  //       frm.dirty();
  //       frm.save();
  //       // frappe.msgprint("Schedule Cancelled")
  //     });
  //     frm.change_custom_button_type("Return", null, "primary");
  //   }
  // },
});
