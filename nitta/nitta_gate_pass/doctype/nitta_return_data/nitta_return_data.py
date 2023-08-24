# Copyright (c) 2023, Ideenkreise and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import date,datetime
from frappe.utils import get_url_to_form
from frappe.desk.notifications import enqueue_create_notification
from frappe.share import add as add_share
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import (
	enqueue_create_notification,
	get_title,
	get_title_html,
)


class NittaReturnData(Document):
	def validate(self):
		if self.item_state=="Select":
			frappe.throw("Select Item Status")
	def after_insert(self):
		self.set_workflow()
		self.save(ignore_permissions=True)
	
	def on_update(self):
		if not self.status=="Draft":
			
			self.update_workflow()
			add_share(self.doctype, self.name, user=self.next_approved_by, read=1, write=1, submit=0, share=1, everyone=0, notify=0)
			notify_assignment(self.next_approved_by,'Nitta Return Data',self.name,self.status)


		self.reload()



	def set_workflow(self):
		workflows=frappe.get_all("Workflow Details",filters={'parent':self.gate_pass},
		fields=['employee','role','department','division'],
		order_by='creation DESC')
		print("workflows",workflows)
		if len(workflows)==0:
			frappe.throw("Set Workflow")
		
		for transition in workflows:
			 # Insert department hod role next
			if (transition.department != "Store") and (transition.department != "Security"):
			
				self.append("workflow", {
							'role': transition['role'],
							'employee': transition['employee'],
							'department': transition['department'],
							'status': 'Pending',
							'division': transition['division']
				})

		for transition in workflows:
        # Insert store hod role last
			if transition.department == 'Store':
				self.append("workflow", {
							'role': transition['role'],
							'employee': transition['employee'],
							'department': transition['department'],
							'status': 'Pending',
							'division': transition['division']
				})

	def update_workflow(self):
		self.current_approval_level=0
		self.max_approval_level=0
		self.status="Initiated"
		self.rejected=False
		
		current_user_index =0
		for index,approval in enumerate(self.workflow,start=1):
			self.max_approval_level+=1
			if approval.status=='Approved':
				self.current_approval_level+=1
			if approval.status=='Rejected':
				self.rejected=True
			if approval.employee ==frappe.session.user and approval.status!='Pending':
				current_user_index=index

		if self.current_approval_level==self.max_approval_level:
			self.next_approval_by=None
			self.status='Final Approved'
			# Upadte gate pass status
			gate_pass=frappe.get_doc("Nitta Gate Pass",self.gate_pass)
			gate_pass.status=self.item_state
			gate_pass.db_update()
			

# Send email to the vendor
    		# vendor_email = self.vendor_email  # Replace with the actual attribute that stores the vendor's email address
   			# subject = "Your Request has been Final Approved"
    		# message = "Your request has been approved. Thank you for your submission."
    
   			#  try:
			# 	frappe.sendmail(
			# 		recipients=[vendor_email],
			# 		subject=subject,
			# 		message=message
			# 	)
        	# 	print("Email sent successfully to vendor.")
    		# except Exception as e:
        	# 	print("Error sending email:", e)
			
			
		elif self.current_approval_level==0:
			
			self.next_approved_by=self.workflow[self.current_approval_level].employee
			if self.rejected:
				# self.status='Level '+str(self.current_approval_level+1)+' Rejected'
				approval_flow = self.workflow[self.current_approval_level]
				self.status='Level '+str(self.current_approval_level+1)+'('+approval_flow.department+'-' +approval_flow.role +')'+' Rejected'
		elif self.current_approval_level<self.max_approval_level:
			self.next_approved_by=self.workflow[self.current_approval_level].employee
			if not self.rejected :
				
				approval_flow = self.workflow[self.current_approval_level-1]
				self.status='Level '+str(self.current_approval_level)+'('+approval_flow.department+'-' +approval_flow.role +')'+' Approved'
	
			else:
				# self.status='Level '+str(self.current_approval_level+1)+' Rejected'
				approval_flow = self.workflow[self.current_approval_level]
				self.status='Level '+str(self.current_approval_level+1)+'('+approval_flow.department+'-' +approval_flow.role +')'+' Rejected'

					
		
			
		self.db_update()


def notify_assignment(shared_by, doctype, doc_name,status):

	if not (shared_by and doctype and doc_name) :
		return

	from frappe.utils import get_fullname

	title = get_title(doctype, doc_name)

	reference_user = get_fullname(frappe.session.user)
	notification_message = _("{0} shared a document {1} {2} with status {3}").format(
		frappe.bold(reference_user), frappe.bold(_(doctype)), get_title_html(title),frappe.bold(_(status))
	)

	notification_doc = {
		"type": "Share",
		"document_type": doctype,
		"subject": notification_message,
		"document_name": doc_name,
		"from_user": frappe.session.user,
		
	}
	
	enqueue_create_notification(shared_by, notification_doc)
				


@frappe.whitelist()
def get_gatepass_details(gate_pass):
	

	dispatch_item=frappe.get_all("Nitta item",filters={'parent':gate_pass},
	fields=['item','work_to_be_done','expected_delivery_date'])
	print("dispatch_item",dispatch_item)
	return dispatch_item

@frappe.whitelist()
def get_gate_pass(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""SELECT name
	FROM `tabNitta Gate Pass` 
	
	
	 """.format(**{
				'key': searchfield
			}), {
			'txt': "%{}%".format(txt),
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len,
			'status':filters["status"]

		})
