# Copyright (c) 2023, Ideenkreise and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.pdf import get_pdf
from frappe.utils.file_manager import get_file,download_file,get_file_path,write_file,save_file
from PyPDF2 import PdfMerger
from frappe.utils import get_site_path
import PyPDF2
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
	def validate(self):
		department=get_employee_details(frappe.session.user)
		#validation for way of Dispatch
		if department:
			for d in department:
				print(d['department'])
		if self.way_of_dispatch is None and d['department']=="Security":
			frappe.throw("Please Select Way of Dispatch")

		# Validation for expected delivery date
		for item in self.item:
			if item.expected_delivery_date < frappe.utils.today():
				frappe.throw("Expected Delivery Date cannot be lesser than the current date for item {}".format(item.pdt_name))


		

	def before_save(self):
		doc= self.get_doc_before_save()
		if(doc):
			if self.status=="Draft":
				if(doc.is_emergency != self.is_emergency):
					self.workflow_name=None
					self.approval_flow=[]
					self.set_workflow()
					self.set_gatepass_no()
			elif doc.status=="Draft" and self.status!=doc.status:
					self.set_gatepass_no()
		

	
	def after_insert(self):
		self.set_workflow()
		self.set_gatepass_no()
		self.save()

	# 	self.doc_name=self.name
	# 	self.set_workflow()
	# 	self.save(ignore_permissions=True)
	
	def on_update(self):
		if self.status=='Initiated':
			self.update_assigned_date(1)
		
		
		if not self.status=="Draft" and not self.status=="Close":
			self.update_workflow()
			
			employee_email=self.user
			add_share(self.doctype, self.name, user=self.next_approved_by, read=1, write=1, submit=0, share=1, everyone=0, notify=0)
			if self.is_emergency:
				notify_emergency(self.next_approved_by,"Nitta Gate Pass",self.name,self.status)
			else:
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
			self.workflow=[]
			
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
			approval.assigned_date=datetime.now()
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
		emergency_dispatch_reminder()
		
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
				self.current_approval_level+=1
			if approval.employee ==frappe.session.user and approval.status!='Pending':
				current_user_index=index

		if self.current_approval_level==self.max_approval_level:
			
			self.next_approval_by=None
			self.status='Dispatched'
			if not self.is_emergency:
			
				# Send mail to vendor
				args={
					"message":"Material Dispatched",
					"vendor":self.vendor,
					"vendor_email":self.vendor_email,
					"items":self.item,
					"gatepass":self.name
				}
				
				frappe.sendmail(template='dispatched',recipients=self.vendor_email,subject="Material Dispatched",args=args)
			notify_Initiator(self.user,"Nitta Gate Pass",self.name)
			if current_user_index>0:
				self.update_updated_date(current_user_index)
			
		elif self.current_approval_level==0:
			

			if self.rejected:
				# frappe.throw(self.rejected)
				approval_flow = self.workflow[self.current_approval_level]
				self.status='Level '+str(self.current_approval_level+1)+'('+approval_flow.department+'-' +approval_flow.role +')'+' Rejected'

				if current_user_index>0:
					self.update_updated_date(current_user_index)
			else:
			
			
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
				if approval_flow.role=="Security" and self.is_emergency:
					# Send mail to vendor (emergency Dispatch)
					args={
						"message":"Material Dispatched",
						"vendor":self.vendor,
						"vendor_email":self.vendor_email,
						"items":self.item,
						"gatepass":self.name
					}
					
					frappe.sendmail(template='dispatched',recipients=self.vendor_email,subject="Material Dispatched",args=args)

			

				if current_user_index>0:
					self.update_updated_date(current_user_index)	
			else:
				
				
				# 'Level '+str(self.current_approval_level+1)+'('+approvaself.status='Level '+str(self.current_approval_level+1)+' Rejected'
				approval_flow = self.workflow[self.current_approval_level]
				# self.status=l_flow.department+'-' +approval_flow.role +')'+' Rejected'
				self.status="Rejected"
				self.next_approved_by=None
				notify_assignment(self.user,'Nitta Gate Pass',self.name,self.status)
				if current_user_index>0:
					self.update_updated_date(current_user_index)
		elif self.current_approval_level==self.max_approval_level:
			self.next_approval_by=None
			self.status='Dispatched'
			if current_user_index>0:
				self.update_updated_date(current_user_index)
			
		self.db_update()

	def set_gatepass_no(self):
		# Get Division Code
		division=frappe.get_doc("Division",self.division)
		# Get Department Code
		department=frappe.get_doc("Department",self.department)
		# Get count
		count=frappe.db.count(self.doctype,{'division':self.division,'department':self.department,'status':['!=','Draft']})
		if not self.status == 'Draft':
			self.gate_pass_no='NT'+'-'+'GP'+'/'+division.division+'/'+department.department+'/'+str(count+1)
		else:
			self.gate_pass_no='NF'+'/'+division.division+'/'+department.department+'/'+self.name

	

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
		print("user",transition.role)
	
	
		# user_role = frappe.db.sql("""
		# SELECT roles, division, department, user FROM `tabEmployee`
		# WHERE roles = %(role)s AND division = %(division)s AND department = %(department)s
		# """, values={'role': transition.role, 'division': division, 'department': employee_department},as_dict=1)
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

def notify_emergency(shared_by, doctype, doc_name,status):

	if not (shared_by and doctype and doc_name) :
		return

	from frappe.utils import get_fullname

	title = get_title(doctype, doc_name)

	reference_user = get_fullname(frappe.session.user)
	notification_message = _("{0} shared a document {1} {2} for Emergency Dispatch ").format(
		frappe.bold(reference_user), frappe.bold(_(doctype)), get_title_html(title)
	)

	notification_doc = {
		"type": "Share",
		"document_type": doctype,
		"subject": notification_message,
		"document_name": doc_name,
		"from_user": frappe.session.user,
		
	}
	
	enqueue_create_notification(shared_by, notification_doc)
def notify_Initiator(shared_by,doctype,doc_name):
	if not (shared_by and doctype and doc_name) :
		return

	from frappe.utils import get_fullname

	title = get_title(doctype, doc_name)

	reference_user = get_fullname(frappe.session.user)
	notification_message = _("Material Dispatched with {0} {1} ").format(
		 frappe.bold(_(doctype)), get_title_html(title)
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
	return frappe.db.sql("""SELECT role.division,role.department,employee.name,role.role,employee.user FROM `tabEmployee` employee inner join `tabEmployee Role` role 
	on employee.name=role.parent
	WHERE  employee.email=%(name)s""",values={'name':name},as_dict=1)


# send reminder for emergency dispatch approval
@frappe.whitelist()
def emergency_dispatch_reminder():
	emergency_gate_pass=frappe.db.sql(""" select gatepass.name,gatepass.user,gatepass.next_approved_by,workflow.status from   `tabNitta Gate Pass` gatepass inner join
 `tabWorkflow Details` workflow on gatepass.name=workflow.parent and gatepass.next_approved_by=workflow.employee where gatepass.is_emergency='1' and workflow.status='Pending';""",as_dict=1)
	
	for gate_pass in emergency_gate_pass:
		
		send_notification(gate_pass['name'],gate_pass['user'],gate_pass['next_approved_by'],'Nitta Gate Pass')

def send_notification(gate_pass,user,next_approved_by,doctype):
	

	if not (user and doctype and gate_pass) :
		return

	from frappe.utils import get_fullname

	title = get_title(doctype, gate_pass)
	

	reference_user = get_fullname(user)
	notification_message = _("<span style='color: red;'>Material Dispatched with {0}  {1} pls approve </span>").format(
		 frappe.bold(_(doctype)), get_title_html(title)
	)

	notification_doc = {
		"type": "Share",
		"document_type": doctype,
		"subject": notification_message,
		"document_name": gate_pass,
		"from_user": user,
		
	}
	
	enqueue_create_notification(next_approved_by, notification_doc)
	
@frappe.whitelist()
def update_gatepass(gate_pass,item,quantity):
		# item=frappe.db.sql("""select remaining from `tabNitta item` where parent=%(gatepass)s 
		# and name=%(name)s """,
		# values={'gatepass':gate_pass,'name':item},as_dict=1)
		# if item:
		# 	print(item[0]['remaining'])
	doc = frappe.get_doc('Nitta item', item)
	doc.remaining =int(doc.remaining)-int(quantity)
	doc.save()

@frappe.whitelist()
def remove_file_backgroud(files):
    if isinstance(files, str):
        files = json.loads(files)
    frappe.enqueue(remove_file, queue='long', files=files)

def remove_file(files):
    for file in files:
        frappe.delete_doc("File", file)



@frappe.whitelist()
def generate_preview(doctype,docname):

	# Creating and saving the Print format to public files folder
    html = frappe.get_print(doctype, docname, 'Nitta Preview', doc=None)
    pdf = get_pdf(html)
    
    # Define the file name for the generated PDF
    pdf_file_name = f'{docname}_preview.pdf'
    
    # Save the PDF file to a public location
    write_file(pdf, pdf_file_name, is_private=0)
    
    # Return the URL of the generated PDF for the user to access
    pdf_file_url = f'/files/{pdf_file_name}'
    return pdf_file_url