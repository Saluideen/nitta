# Copyright (c) 2023, Ideenkreise and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Employee(Document):
	# pass
	def on_update(self):
		if not self.user:
			user = frappe.new_doc('User')
			user.email = self.email
			user.first_name = self.employee_name
			user.phone = self.phone_number
			user.send_welcome_email=False
			user.enabled=self.enabled
			user.new_password = self.get_password('password')
			user.append('roles',{'role':'Nitta User'})
			user_roles=[]
			user_division=[]
			for role in self.roles:
				user.append('roles',{'role':role.role})
			inserted_user=user.insert(ignore_permissions=True)

			if(inserted_user):
				inserted_user.user_type='System User'
				inserted_user.module_profile='Nitta Profile Module'
				updated_user=inserted_user.save(ignore_permissions=True)
		
			self.user=inserted_user.name
			self.db_update()
		else:
			user = frappe.get_doc('User',self.user)
			user.first_name = self.employee_name
			user.phone = self.phone_number
			user.enabled=self.enabled
			user.new_password = self.get_password('password')
			user.roles=None
			user.append('roles',{'role':'Nitta User'})
			for role in self.roles:
				user.append('roles',{'role':role.role})
			updated_user=user.save(ignore_permissions=True)


@frappe.whitelist()
def get_department(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""SELECT  department
	FROM `tabEmployee Role` 
	WHERE division = %(division)s AND department=%(department)s GROUP BY role
	
	 """.format(**{
				'key': searchfield
			}), {
			'txt': "%{}%".format(txt),
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len,
			'division':filters["division"],
			'department':filters['department']

		})

