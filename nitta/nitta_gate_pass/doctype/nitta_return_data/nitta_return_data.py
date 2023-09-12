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
		
		
		department=get_employee_details(frappe.session.user)
		if department:
			for d in department:
		#validation for item state
				if self.item_state=="Select" and d['department']=="Store":
					frappe.throw("Select Gatepass Status")
				#validation for way of Return
				if self.way_of_return is None and d['department']=="Security":
					frappe.throw("Please Select Way of Return")
		# validation for closed gatepass	
		Gate_pass_status=frappe.get_all("Nitta Gate Pass",filters={'name':self.gate_pass},
		fields=['status'])
		for status in Gate_pass_status:
			
			if status['status']=="Close":
				frappe.throw("Gate Pass Already Closed")
		#Validation for item quantity
		for item in self.product:
			if item.return_quantity is not None and item.quantity is not None:
   
				if int(item.return_quantity) > int(item.quantity):
					frappe.throw("Item return quantity is greater than quantity")

		

	# def before_save(self):

		
	# 	for item in self.product:
	# 		if item.status == "Assembled" or item.status == "Completed":
	# 			self.item_state = "Close"
				
	# 		elif item.status == "Partially Completed":
	# 			self.item_state = "Partially Completed"
				
				
	# 		else:
	# 			self.item_state = "Select"
			
	def after_insert(self):
		
		self.set_workflow()
		self.save(ignore_permissions=True)
	
	def on_update(self):
		delay_reminder()
		last_update=self.get_doc_before_save()
		for product in last_update.product:
			for p in self.product:
				print(p.status)
				if p.return_quantity is None:
					p.return_quantity=0
				if p.name == product.name and p.remaining_quantity != product.remaining_quantity and p.status!=product.status:
				# if(p.name == product.name and p.remaining_quantity != product.remaining_quantity):
					doc = frappe.get_doc('Nitta item', p.item_name)
					doc.remaining =float(product.remaining_quantity) - float(p.return_quantity)
					doc.status=product.status
					print(p.status)
					doc.db_update()
				else:
					doc = frappe.get_doc('Nitta item',p.item_name)
					doc.remaining =p.remaining_quantity
					doc.status=p.status
					print(p.status)
					doc.db_update()


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
		


	def update_assigned_date(self,index):
		approval_flow=frappe.get_all("Return workflow",filters={'parent':self.name,'parenttype':self.doctype,'idx':index})
		if len(approval_flow)>0:
			approval=frappe.get_doc("Return workflow",approval_flow[0].name)
			approval.assigned_date=datetime.now()
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
		if transition.department=="FROM GATEPASS":
			employee_department=department
		else:
			employee_department=transition.department
	
		user_role=frappe.db.sql("""
		SELECT er.role,er.division,er.department,e.user as employee FROM `tabEmployee` e INNER JOIN `tabEmployee Role` er ON er.parent=e.name
		 WHERE e.enabled =1 AND er.role=%(role)s AND er.division=%(division)s  AND er.department=%(department)s 
		""",values={'role': transition.role, 'division': division, 'department': employee_department},as_dict=1)
		if user_role:  # Check if user_role list is not empty
			data.append({'role': user_role[0].role,'division': user_role[0].division, 'user': user_role[0].employee, 'department': user_role[0].department})

	
	
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
	dispatch_item=frappe.get_all("Nitta item",filters={'parent':gate_pass},
	fields=['item','work_to_be_done','expected_delivery_date','quantity','remaining','name','status'])

	return dispatch_item,gate_pass_details

@frappe.whitelist()
def get_employee_details(name):
	employee_details=frappe.db.sql("""select er.department from `tabEmployee` em inner join
	`tabEmployee Role` er on em.name=er.parent where user=%(name)s""",
	values={'name':name},as_dict=1)
	return employee_details


# scheduler for delay mail

def delay_reminder():
	
	
	delayed_gate_pass=frappe.db.sql("""select gate_pass.name,gate_pass.division,gate_pass.department,
	gate_pass.owner,gate_pass.vendor,gate_pass.vendor_email,
		pdt.pdt_name as item,
		pdt.work_to_be_done,
		pdt.quantity,
		pdt.remaining,
		pdt.expected_delivery_date,
		DATEDIFF(CURDATE(), pdt.expected_delivery_date) AS delay
		from `tabNitta Gate Pass`  gate_pass inner join `tabNitta item` pdt on gate_pass.name=pdt.parent
        
        
		where gate_pass.status !="Close" and gate_pass.status !="Rejected" and pdt.status!='Completed' and pdt.status!='Assembled' 
		and ( DATEDIFF(CURDATE(), pdt.expected_delivery_date)='31' or DATEDIFF(CURDATE(), pdt.expected_delivery_date)='75' or
		DATEDIFF(CURDATE(), pdt.expected_delivery_date)='91' )""",as_dict=1)
	# Create a dictionary to group items based on vendor_email
	vendor_items = {}
	division_group={}

	# Iterate through the delayed_gate_pass results
	for gate_pass_info in delayed_gate_pass:
		vendor_email = gate_pass_info["vendor_email"]
		division=gate_pass_info["division"]
		item_info = {
			"gatepass":gate_pass_info["name"],
			"item": gate_pass_info["item"],
			"work_to_be_done": gate_pass_info["work_to_be_done"],
			"quantity":gate_pass_info["quantity"],
			"remaining":gate_pass_info["remaining"],
			"expected_delivery_date": gate_pass_info["expected_delivery_date"],
			"delay": gate_pass_info["delay"],
			"vendor":gate_pass_info["vendor"],
			"vendor_email":gate_pass_info["vendor_email"],
			"department":gate_pass_info["department"],
			
		}

		# Check if the vendor_email already exists in the vendor_items dictionary
		if vendor_email in vendor_items:
			# If it exists, append the item info to the existing list of items
			vendor_items[vendor_email].append(item_info)
		else:
			# If it doesn't exist, create a new entry in the dictionary
			vendor_items[vendor_email] = [item_info]

		if division in division_group:
			division_group[division].append(gate_pass_info)
		else:
			division_group[division] = [gate_pass_info]

	# Iterate through the division groups and send emails to Finance Heads
	for division, gate_pass_list in division_group.items():
		# Assuming you have a function to fetch the Finance Head's email address based on the division
		finance_head_email_data = get_finance_head_email(division)
		if finance_head_email_data:
			finance_head_email=finance_head_email_data[0]['email']
		else:
			frappe.throw("Employee Not Found in Finance Department")
		# Send the email to the Finance Head of the division
		
		args={
				"division":division,
				"items":gate_pass_list,
				"gate_pass_link":get_url_to_form('Nitta Gate Pass',gate_pass_info['name'])
				}
		print("gate_pass_link",get_url_to_form('Nitta Gate Pass', gate_pass_info['name']))
		subject = "Delayed Gate Pass Information for Division: " + division
		
		frappe.sendmail(template='finance',
			recipients=finance_head_email,
			subject=subject,
			args=args
		)
		


	# Send delay mail to vendor	
	subject = "Delayed Gate Pass Information"
	# Iterate through the 'vendor_items' dictionary and send emails
	for vendor_email, items_list in vendor_items.items():
		
		args={
			
			'vendor':item_info['vendor'],
			'vendor_email':vendor_email,
			'items':items_list
		}
		# Send  email to vendor
		frappe.sendmail(template='delay',
			recipients=vendor_email,
			subject=subject,
			args=args
			
		)
	



def get_finance_head_email(division):
	finance_head_email= frappe.db.sql("""select em.email from `tabEmployee` em 
	inner join `tabEmployee Role` er on em.name=er.parent  where er.division=%(division)s and er.department='Finance' and er.role='HOD' """,
	values={'division':division},as_dict=1)

	return finance_head_email

