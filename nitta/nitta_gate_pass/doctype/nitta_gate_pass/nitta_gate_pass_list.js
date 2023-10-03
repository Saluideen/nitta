frappe.listview_settings['Nitta Gate Pass'] = {
    add_fields: ['status'],
    hide_name_column: true,
    get_indicator(doc) {
      

    if (doc.status == 'Initiated')
        return [doc.status, 'yellow', 'status,=,' + doc.status];

    if (doc.status.includes('Dispatched'))
        return [doc.status, 'green', 'status,like,' + doc.status];

    if (doc.status.includes('Partially Completed'))
        return [doc.status, 'orange', 'status,like,' + doc.status];

    if (doc.status.includes('Close'))
        return [doc.status, 'blue', 'status,like,' + doc.status];

    },
}