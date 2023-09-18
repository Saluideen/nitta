frappe.listview_settings['Nitta Return Data'] = {
    add_fields: ['status'],
    hide_name_column: true,
    get_indicator(doc) {
      

    if (doc.status == 'Initiated')
        return [doc.status, 'yellow', 'status,=,' + doc.status];

    if (doc.status.includes('Final Approved'))
        return [doc.status, 'orange', 'status,like,' + doc.status];

   

   

    },
}