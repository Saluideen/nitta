# Copyright (c) 2023, Ideenkreise and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Department(Document):
	pass
@frappe.whitelist()
def get_department(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""SELECT name FROM `tabDepartment` where name!='FROM GATEPASS' """)
