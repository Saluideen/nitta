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


class NittaGatePass(Document):
	# pass
	def after_insert(self):
		self.doc_name=self.name
		self.set_workflow()
		self.save(ignore_permissions=True)
	# pass
	def on_update(self):
		
		
		if not self.status=="Draft" and not self.status=="Close":
			self.update_workflow()
			employee_email=self.user
			add_share(self.doctype, self.name, user=self.next_approved_by, read=1, write=1, submit=0, share=1, everyone=0, notify=0)
			notify_assignment(self.next_approved_by,'Nitta Gate Pass',self.name,self.status)


		self.reload()
	
	def set_workflow(self):
		if self.is_emergency:
			self.workflow_type="Emergency Dispatch"
		else:
			self.workflow_type="Dispatch"

		
		workflows=frappe.get_all("Nitta Workflow",filters={"division":self.division,"department":self.department,"type":self.workflow_type},fields=["name"])
		
		if len(workflows)==0:
			frappe.throw("Set Dispatch Workflow")
		if len(workflows)>0:
			self.workflow_name=workflows[0].name
			
			workflow_transitions=get_workflow_transition(self.workflow_name)
			for transition in workflow_transitions['data']:
				
				
				self.append("workflow", {'role': transition['role'],
						'employee': transition['user'],
						'department': transition['department'],
						'status':'Pending',
						'role':transition['role'],
						'division':transition['division']
						})
			# self.retrun_workflow()

	def retrun_workflow(self):
		 # Iterate through the workflow records and reorder them as required

		for transition in self.workflow:
        # Insert department hod role next
			if transition.department ==self.department:
				self.append("return_workflow", {
					'role': transition.role,
					'employee': transition.employee,
					'department': transition.department,
					'status': 'Pending',
					'division': transition.division
				})
		for transition in self.workflow:
        # Insert store hod role last
			if transition.department == 'Store':
				self.append("return_workflow", {
					'role': transition.role,
					'employee': transition.employee,
					'department': transition.department,
					'status': 'Pending',
					'division': transition.division
				})



	def update_assigned_date(self,index):
		approval_flow=frappe.get_all("Workflow Details",filters={'parent':self.name,'parenttype':self.doctype,'idx':index})
		
		if len(approval_flow)>0:
			approval=frappe.get_doc("Workflow Details",approval_flow[0].name)
			approval.assigned_date=datetime.now()
			res=approval.save(ignore_permissions=True)
			
		else:
			frappe.throw("Assign Approval flow")

	

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
				self.update_assigned_date(self.current_approval_level+1)
				if current_user_index>0:
					self.update_assigned_date(current_user_index)	
				# self.status='Level '+str(self.current_approval_level)+' Approved'
				approval_flow = self.workflow[self.current_approval_level-1]
				self.status='Level '+str(self.current_approval_level)+'('+approval_flow.department+'-' +approval_flow.role +')'+' Approved'


			

				if current_user_index>0:
					self.update_assigned_date(current_user_index)	
			else:
				# self.status='Level '+str(self.current_approval_level+1)+' Rejected'
				approval_flow = self.workflow[self.current_approval_level]
				self.status='Level '+str(self.current_approval_level+1)+'('+approval_flow.department+'-' +approval_flow.role +')'+' Rejected'

				if current_user_index>0:
					self.update_assigned_date(current_user_index)	
		elif self.current_approval_level==self.max_approval_level:
			self.next_approval_by=None
			self.status='Final Approved'
			frappe.sendmail(template='Approved',subject="Request for Approval of "+self.name,recipients=[self.vendor_email],args=args)
			# # self.send_final_mail()
			# if current_user_index>0:
			# 	self.update_updated_date(current_user_index)	
			# # Copy Sharing
			# is_copy_to = frappe.get_all('Nitta CC',filters={'parent':self.name,'parenttype':self.doctype},fields=['nitta_user'])
			# for copy in is_copy_to:
			# 	# Doc Share For CC user
			# 	add_share(self.doctype, self.name, user=copy.nitta_user, read=1, write=1, submit=0, share=1, everyone=0, notify=0)
		self.db_update()
	

	def update_return_workflow(self):
		
		# self.retrun_workflow()
		self.current_approval_level=0
		self.max_approval_level=0
		self.status="Return"
		self.rejected=False
		
		current_user_index =0
		for index,approval in enumerate(self.return_workflow,start=1):
			self.max_approval_level+=1
			if approval.status=='Approved':
				self.current_approval_level+=1
			if approval.status=='Rejected':
				self.rejected=True
			if approval.employee ==frappe.session.user and approval.status!='Pending':
				current_user_index=index

		if self.current_approval_level==self.max_approval_level:
			self.next_approval_by=None
			self.status='Close'
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
			
			self.next_approved_by=self.return_workflow[self.current_approval_level].employee
			if self.rejected:
				# self.status='Level '+str(self.current_approval_level+1)+' Rejected'
				approval_flow = self.return_workflow[self.current_approval_level]
				self.status='Level '+str(self.current_approval_level+1)+'('+approval_flow.department+'-' +approval_flow.role +')'+' Rejected'
		elif self.current_approval_level<self.max_approval_level:
			self.next_approved_by=self.return_workflow[self.current_approval_level].employee
			if not self.rejected :
				# self.update_assigned_date(self.current_approval_level+1)
				# if current_user_index>0:
				# 	# self.update_assigned_date(current_user_index)	
				# self.status='Level '+str(self.current_approval_level)+' Approved'
				approval_flow = self.return_workflow[self.current_approval_level-1]
				self.status='Level '+str(self.current_approval_level)+'('+approval_flow.department+'-' +approval_flow.role +')'+' Approved'


			

				# if current_user_index>0:
					# self.update_assigned_date(current_user_index)	
			else:
				# self.status='Level '+str(self.current_approval_level+1)+' Rejected'
				approval_flow = self.return_workflow[self.current_approval_level]
				self.status='Level '+str(self.current_approval_level+1)+'('+approval_flow.department+'-' +approval_flow.role +')'+' Rejected'

				# if current_user_index>0:
					# self.update_assigned_date(current_user_index)	
		# elif self.current_approval_level==self.max_approval_level:
		# 	self.next_approval_by=None
		# 	self.status='Final Approved'
		# 	frappe.sendmail(template='Approved',subject="Request for Approval of "+self.name,recipients=[self.vendor_email],args=args)
		# 	# # self.send_final_mail()
			# if current_user_index>0:
			# 	self.update_updated_date(current_user_index)	
			# # Copy Sharing
			# is_copy_to = frappe.get_all('Nitta CC',filters={'parent':self.name,'parenttype':self.doctype},fields=['nitta_user'])
			# for copy in is_copy_to:
			# 	# Doc Share For CC user
			# 	add_share(self.doctype, self.name, user=copy.nitta_user, read=1, write=1, submit=0, share=1, everyone=0, notify=0)
		self.db_update()


	

	


@frappe.whitelist()
def get_workflow_transition(workflow_name):
	
	transitions=frappe.get_all('Transition Rule',filters={'parent':workflow_name,'parenttype':'Nitta Workflow'},fields=['role','department','division'],order_by='idx')	
	data=[]
	for transition in transitions:
	
		user_role = frappe.db.sql("""
		SELECT roles, division, department, user FROM `tabEmployee`
		WHERE roles = %(role)s AND division = %(division)s AND department = %(department)s
		""", values={'role': transition.role, 'division': transition.division, 'department': transition.department},as_dict=1)
		if user_role:  # Check if user_role list is not empty
			data.append({'role': user_role[0].roles,'division': user_role[0].division, 'user': user_role[0].user, 'department': user_role[0].department})

	
	
	return {'Status':True,'data':data}


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
def get_employee_details(name):
	return frappe.db.sql("""SELECT division,department,name,roles,user FROM `tabEmployee` 
	WHERE  email=%(name)s""",values={'name':name},as_dict=1)