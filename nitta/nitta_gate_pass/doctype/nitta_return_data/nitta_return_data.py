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
		#validation for item state
		if self.item_state=="Select" and self.department_store=="Store":
			frappe.throw("Select Item Status")
		# validation for closed gatepass	
		Gate_pass_status=frappe.get_all("Nitta Gate Pass",filters={'name':self.gate_pass},
		fields=['status'])
		for status in Gate_pass_status:
			print("Status",status['status'])
			if status['status']=="Close":
				frappe.throw("Gate Pass Already Closed")
		#Validation for item quantity
		for item in self.product:
			if item.return_quantity is not None and item.quantity is not None:
   
				if int(item.return_quantity) > int(item.quantity):
					frappe.throw("Item return quantity is greater than quantity")

		#validation for way of Return
		if self.way_of_dispatch is None and self.department_store=="Security":
			frappe.throw("Please Select Way of Return")

		
			
	def after_insert(self):
		self.set_workflow()
		self.save(ignore_permissions=True)
	
	def on_update(self):
		if self.status=='Initiated':
			self.update_assigned_date(1)
		if not self.status=="Draft":
			
			self.update_workflow()
			add_share(self.doctype, self.name, user=self.next_approved_by, read=1, write=1, submit=0, share=1, everyone=0, notify=0)
			notify_assignment(self.next_approved_by,'Nitta Return Data',self.name,self.status)


		self.reload()



	def set_workflow(self):
		workflows=frappe.get_all("Nitta Workflow",filters={"type":"Return"},fields=["name"])
		
		if len(workflows)==0:
			frappe.throw("Set Workflow")
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
		# workflows=frappe.get_all("Workflow Details",filters={'parent':self.gate_pass},
		# fields=['employee','role','department','division'],
		# order_by='creation DESC')
		# print("workflows",workflows)
		# if len(workflows)==0:
		# 	frappe.throw("Set Workflow")
		
		# for transition in workflows:
		# 	 # Insert department hod role next
		# 	if (transition.department != "Store") and (transition.department != "Security"):
			
		# 		self.append("workflow", {
		# 					'role': transition['role'],
		# 					'employee': transition['employee'],
		# 					'department': transition['department'],
		# 					'status': 'Pending',
		# 					'division': transition['division']
		# 		})

		# for transition in workflows:
        # # Insert store hod role last
		# 	if transition.department == 'Store':
		# 		self.append("workflow", {
		# 					'role': transition['role'],
		# 					'employee': transition['employee'],
		# 					'department': transition['department'],
		# 					'status': 'Pending',
		# 					'division': transition['division']
		# 		})


	def update_assigned_date(self,index):
		approval_flow=frappe.get_all("Return workflow",filters={'parent':self.name,'parenttype':self.doctype,'idx':index})
		if len(approval_flow)>0:
			approval=frappe.get_doc("Return workflow",approval_flow[0].name)
			approval.assigned_date=date.today()
			approval.save()
		else:
			frappe.throw("Assign Approval flow")

	def update_updated_date(self,index):
		approval_flow=frappe.get_all("Return workflow",filters={'parent':self.name,'parenttype':self.doctype,'idx':index})
		if len(approval_flow)>0:
			approval=frappe.get_doc("Return workflow",approval_flow[0].name)
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
			# Upadte gate pass status
			gate_pass=frappe.get_doc("Nitta Gate Pass",self.gate_pass)
			gate_pass.status=self.item_state
			gate_pass.db_update()
	
			
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
					self.update_updated_date(current_user_index)
				
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
def get_gatepass_details(gate_pass):
	gate_pass_details=frappe.db.sql("""select * from `tabNitta Gate Pass`  where name=%(name)s""",
	values={"name":gate_pass},as_dict=1)

	# check if  return document aganist gatepass
	return_gate_pass = frappe.get_all("Nitta Return Data", 
                                   filters={'gate_pass': gate_pass},
								   fields=['name'],
                                   order_by='creation desc',
                                   limit=1)

	if return_gate_pass:
		print(return_gate_pass[0]['name'])
		dispatch_item=frappe.get_all("Return product Details",filters={'parent':return_gate_pass[0]['name']},
		fields=['item','work_to_be_done','quantity','return_quantity','previous_return_quantity','remaining_quantity','remarks'])
	else:
		dispatch_item=frappe.get_all("Nitta item",filters={'parent':gate_pass},
		fields=['item','work_to_be_done','expected_delivery_date','quantity'])

	return dispatch_item,gate_pass_details

@frappe.whitelist()
def get_employee_details(name):
	print(name)
	employee_details=frappe.db.sql("""select * from `tabEmployee` where user=%(name)s""",
	values={'name':name},as_dict=1)
	return employee_details