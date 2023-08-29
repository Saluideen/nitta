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
		if self.status=='Initiated':
			self.update_assigned_date(1)
		
		
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

		
		workflows=frappe.get_all("Nitta Workflow",filters={"type":self.workflow_type},fields=["name"])
		
		if len(workflows)==0:
			frappe.throw("Set Dispatch Workflow")
		if len(workflows)>0:
			self.workflow_name=workflows[0].name
			
			workflow_transitions=get_workflow_transition(self.workflow_name,self.department,self.division)
			for transition in workflow_transitions['data']:
				
				
				self.append("workflow", {'role': transition['role'],
						'employee': transition['user'],
						'department': transition['department'],
						'status':'Pending',
						'role':transition['role'],
						'division':transition['division']
						})

	


	def update_assigned_date(self,index):
		approval_flow=frappe.get_all("Workflow Details",filters={'parent':self.name,'parenttype':self.doctype,'idx':index})
		if len(approval_flow)>0:
			approval=frappe.get_doc("Workflow Details",approval_flow[0].name)
			approval.assigned_date=date.today()
			approval.save()
		else:
			frappe.throw("Assign Approval flow")

	def update_updated_date(self,index):
		approval_flow=frappe.get_all("Workflow Details",filters={'parent':self.name,'parenttype':self.doctype,'idx':index})
		if len(approval_flow)>0:
			approval=frappe.get_doc("Workflow Details",approval_flow[0].name)
			approval.updated_date=datetime.now()
			approval.save()
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
			if current_user_index>0:
				self.update_updated_date(current_user_index)
			
		elif self.current_approval_level==0:
			
			self.next_approved_by=self.workflow[self.current_approval_level].employee
			
		elif self.current_approval_level<self.max_approval_level:
			self.next_approved_by=self.workflow[self.current_approval_level].employee
			if not self.rejected :
				self.update_assigned_date(self.current_approval_level+1)
				if current_user_index>0:
					self.update_updated_date(current_user_index)	
				# self.status='Level '+str(self.current_approval_level)+' Approved'
				approval_flow = self.workflow[self.current_approval_level-1]
				self.status='Level '+str(self.current_approval_level)+'('+approval_flow.department+'-' +approval_flow.role +')'+' Approved'


			

				if current_user_index>0:
					self.update_updated_date(current_user_index)	
			else:
				# self.status='Level '+str(self.current_approval_level+1)+' Rejected'
				approval_flow = self.workflow[self.current_approval_level]
				self.status='Level '+str(self.current_approval_level+1)+'('+approval_flow.department+'-' +approval_flow.role +')'+' Rejected'

				if current_user_index>0:
					self.update_updated_date(current_user_index)
		elif self.current_approval_level==self.max_approval_level:
			self.next_approval_by=None
			self.status='Final Approved'
			if current_user_index>0:
				self.update_updated_date(current_user_index)
			
		self.db_update()
	

@frappe.whitelist()
def get_workflow_transition(workflow_name,department,division):
	
	transitions=frappe.get_all('Transition Rule',filters={'parent':workflow_name,'parenttype':'Nitta Workflow'},fields=['role','department'],order_by='idx')	
	data=[]
	for transition in transitions:
		if transition.department=="current_department":
			employee_department=department
		else:
			employee_department=transition.department
	
		user_role = frappe.db.sql("""
		SELECT roles, division, department, user FROM `tabEmployee`
		WHERE roles = %(role)s AND division = %(division)s AND department = %(department)s
		""", values={'role': transition.role, 'division': division, 'department': employee_department},as_dict=1)
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