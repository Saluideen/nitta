// // Copyright (c) 2023, Ideenkreise and contributors
// // For license information, please see license.txt

frappe.ui.form.on("Nitta Gate Pass", {
  refresh: function (frm) {
  //  hide connection + icon
    $(".btn.btn-new.btn-secondary.btn-xs.icon-btn").hide();
    // hide connection based on status
    if (frm.doc.status !== "Dispatched" && frm.doc.status !== "Partially Completed" && frm.doc.status !== "Close") {
      frm.dashboard.hide();
  }
  
   


    // Check if the date field is empty before setting the current date
    if (!frm.doc.from_date) {
      var currentDate = frappe.datetime.get_today();
      frm.set_value("from_date", currentDate);
    }

    if (roles.includes("Security")) {
      frm.set_df_property("way_of_dispatch", "hidden", 0);
    }
    if (frm.is_new()) {
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

    // if (frm.doc.status == "Draft") {
    //   frm.refresh()
    //   frm.set_df_property("workflow_name", "hidden", 0);
    //   frm.set_df_property("workflow", "hidden", 0);
    //   frm.set_df_property("next_approved_by", "hidden", 0);
    //   frm.set_df_property("status", "hidden", 0);
    // }

    // Initiate only creator.
    if (!frm.is_new() && frm.doc.status == "Draft" && roles.includes("User")) {
      cur_frm.page.add_action_item("Initiate", function () {
        frm.doc.status = "Initiated";
        frm.refresh_field("status");
        frm.dirty();
        frm.save();
      });
      frm.change_custom_button_type("Initiate", null, "primary");
    }

    if (frm.doc.status != "Draft" && !roles.includes("Security")) {
      frm.disable_save();
      frm.disable_form();
    }

    if (frm.doc.status == "Dispatched" && roles.includes("Security")) {
      frm.disable_save();
      frm.disable_form();
    }
    if (frm.doc.status == "Close" && roles.includes("Security")) {
      frm.disable_save();
      frm.disable_form();
    }
    if (roles.includes("Security")) {
      frm.set_df_property("from_date", "read_only", 1);
      frm.set_df_property("is_emergency", "read_only", 1);
      frm.set_df_property("vendor", "read_only", 1);
      frm.set_df_property("item", "read_only", 1);
      frm.set_df_property("workflow", "read_only", 1);
    }

    if (
      frm.doc.next_approved_by == frappe.session.user &&
      frm.doc.status != "Dispatched" &&
      frm.doc.status != "Close" &&
      frm.doc.status != "Partially Completed"
    ) {
      frm.page.add_action_item("Approve", () => {
        let index = frm.doc.workflow.findIndex(
          (el) => el.employee == frappe.session.user && el.status != "Approved"
        );
        frm.doc.workflow[index].status = "Approved";
        frm.refresh_field("workflow");
        frm.dirty();
        frm.save();
      });
      frm.change_custom_button_type("Approve", null, "primary");

      if (frm.doc.status == "Initiated" && !frm.doc.is_emergency) {
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


  uploadPrivateFile: async function (frm) {
		let file_doc = await new Promise((resolve, reject) => {
			new frappe.ui.FileUploader({
				doctype: frm.doctype,
				docname: frm.docname,
				allow_multiple: false,
				restrictions: {
					allowed_file_types: [".png", ".jpeg",".jpg"]
				},
				folder: 'Home/Attachments',
				on_success: (file_doc) => {
					if (file_doc.file_url.includes('/private/')) {
						resolve(file_doc);
					} else {
						frappe.call({
							method: 'nitta.nitta_gate_pass.doctype.nitta_gate_pass.nitta_gate_pass.remove_file_backgroud',
							args: {
								files: [file_doc.name],
							},
							freeze: true,
							callback: (r) => {
								frappe.msgprint("select Private file")
							},
							error: (r) => {
								frappe.msgprint(r)
							}
						})
					}
				}
			});
		});
		return file_doc;
	},


});
frappe.ui.form.on("Nitta item", {
  quantity: function (frm, cdt, cdn) {
    var row = locals[cdt][cdn];

    frappe.model.set_value(cdt, cdn, "remaining", row.quantity);
  },

  download: function (frm, cdt, cdn) {
    let child = locals[cdt][cdn];
    window.open(child.attachment);
  },
  upload: async function (frm, cdt, cdn) {
		
			let file_doc = await frm.events.uploadPrivateFile(frm);
			frappe.model.set_value(cdt, cdn, "attachment", file_doc.file_url);
			frappe.model.set_value(cdt, cdn, "file_name", file_doc.name);
  }
		
});
