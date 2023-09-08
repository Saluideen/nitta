# Copyright (c) 2023, Ideenkreise and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class Designation(Document):
	def validate(self):
		new_role=frappe.new_doc('Role')
		new_role.role_name=self.role
		new_role.save(ignore_permissions=True)
