# Copyright (c) 2023, Ideenkreise and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Division(Document):
	pass
@frappe.whitelist()
def get_division(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""SELECT name FROM `tabDivision` order by name """)
