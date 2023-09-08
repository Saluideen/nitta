// Copyright (c) 2023, Ideenkreise and contributors
// For license information, please see license.txt
// Declare department_store globally

frappe.ui.form.on("Nitta Return Data", {
  refresh: function (frm) {
    // Check if the date field is empty before setting the current date
    if (!frm.doc.from_date) {
      var currentDate = frappe.datetime.get_today();
      frm.set_value("from_date", currentDate);
    }
    // set current user department if department is store change some field state
    frm.events.store_department(frm);

    // initiate button
    frm.events.initiate_button(frm);
    // hide security role fields
    frm.events.hide_security(frm);
    // approve Button
    frm.events.approve_button(frm);
    //  apply filter in department field
    frm.events.department_filter(frm);
  },

  // hide fields
  way_of_return: function (frm) {
    let way_of_dispatch = frm.doc.way_of_return;
    if (way_of_dispatch == "By Hand") {
      frm.set_df_property("recipient_name", "hidden", 0);
      frm.set_df_property("phone", "hidden", 0);
      frm.set_df_property("courier_number", "hidden", 1);
      frm.set_df_property("driver_name", "hidden", 1);
      frm.set_df_property("contact_number", "hidden", 1);
      frm.set_df_property("registration_number", "hidden", 1);
    } else if (way_of_dispatch == "Vehicle") {
      frm.set_df_property("driver_name", "hidden", 0);
      frm.set_df_property("contact_number", "hidden", 0);
      frm.set_df_property("registration_number", "hidden", 0);
      frm.set_df_property("recipient_name", "hidden", 1);
      frm.set_df_property("phone", "hidden", 1);
      frm.set_df_property("courier_number", "hidden", 1);
    } else {
      frm.set_df_property("courier_number", "hidden", 0);
      frm.set_df_property("driver_name", "hidden", 1);
      frm.set_df_property("contact_number", "hidden", 1);
      frm.set_df_property("registration_number", "hidden", 1);
      frm.set_df_property("recipient_name", "hidden", 1);
      frm.set_df_property("phone", "hidden", 1);
    }
  },

  // insert gate pass material details in return document
  gate_pass: function (frm) {
    frappe.call({
      method:
        "nitta.nitta_gate_pass.doctype.nitta_return_data.nitta_return_data.get_gatepass_details",
      args: {
        gate_pass: frm.doc.gate_pass,
      },
      callback: function (r) {
        console.log(r.message[1]);

        r.message[0].forEach((el) => {
          frm.add_child("product", {
            item: el.item,
            work_to_be_done: el.work_to_be_done,
            quantity: el.quantity,
            remaining_quantity: el.remaining,
            remarks: el.remarks,
            previous_return_quantity: el.return_quantity,
            expected_delivery_date: el.expected_delivery_date,
            item_name: el.name,
            previous_remaining: el.remaining,
          });

          frm.refresh_field("product");
          // }
        });
        r.message[1].forEach((el) => {
          frm.set_value("department", el.department);
          frm.set_value("division", el.division);
        });
      },
    });
  },
  ////////////////////////////////////////custom functions///////////////////////////////////////////////////////
  store_department: function (frm) {
    frappe.call({
      method:
        "nitta.nitta_gate_pass.doctype.nitta_return_data.nitta_return_data.get_employee_details",
      async: false,
      args: {
        name: frappe.session.user,
      },
      callback: function (r) {
        if (r.message[0].department == "Store") {
          frm.set_df_property("item_state", "hidden", 0);
          frm.set_df_property("from_date", "read_only", 1);
          frm.set_df_property("vendor_name", "read_only", 1);
          frm.set_df_property("workflow", "read_only", 1);
          frm.set_df_property("product", "read_only", 0);
        }
        if (frm.doc.status !== "Draft" && r.message[0].department != "Store") {
          frm.disable_save();
          frm.disable_form();
        }
        if (
          frm.doc.status == "Final Approved" &&
          r.message[0].department == "Store"
        ) {
          frm.disable_save();
          frm.disable_form();
        }
      },
    });
  },
  initiate_button: function (frm) {
    if (!frm.is_new() && frm.doc.status == "Draft") {
      cur_frm.page.add_action_item("Initiate", function () {
        frm.doc.status = "Initiated";
        frm.refresh_field("status");
        frm.dirty();
        frm.save();
      });
      frm.change_custom_button_type("Initiate", null, "primary");
    }
  },
  hide_security: function (frm) {
    if (roles.includes("Security")) {
      frm.set_df_property("way_of_return", "hidden", 0);
      frm.set_df_property("product", "hidden", 1);
      frm.set_df_property("from_date", "read_only", 1);
      frm.set_df_property("vendor_name", "read_only", 1);
      frm.set_df_property("workflow", "read_only", 1);
    }
  },
  approve_button: function (frm) {
    if (
      frm.doc.next_approved_by == frappe.session.user &&
      frm.doc.status != "Final Approved"
    ) {
      frm.page.add_action_item("Approve ", () => {
        let index = frm.doc.workflow.findIndex(
          (el) => el.employee == frappe.session.user && el.status != "Approved"
        );
        frm.doc.workflow[index].status = "Approved";
        frm.refresh_field("workflow");
        frm.dirty();
        frm.save();
      });
    }
  },
  department_filter: function (frm) {
    frm.set_query("gate_pass", function () {
      return {
        filters: { status: ["in", ["Dispatched", "Partially Completed"]] },
      };
    });
  },
});
frappe.ui.form.on("Return product Details", {
  return_quantity: function (frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    let remains =
      (parseFloat(row.remaining_quantity) || 0) -
      (parseFloat(row.return_quantity) || 0);
    let previous =
      (parseFloat(row.previous_remaining) || 0) -
      (parseFloat(row.return_quantity) || 0);
    if ((remains = previous)) {
      frappe.model.set_value(cdt, cdn, "remaining_quantity", remains);
    } else {
      frappe.model.set_value(cdt, cdn, "remaining_quantity", previous);
    }
  },
});
