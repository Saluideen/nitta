# Copyright (c) 2023, Ideenkreise and contributors
# For license information, please see license.txt

import frappe
from datetime import date,datetime,timedelta
from dataclasses import dataclass


def execute(filters=None):
	columns, data = [], []
	columns=get_columns()
	data=get_data(filters)
	chart=get_chart(data)
	summary=get_summary(data)
	return columns, data, None, chart, summary
	

def get_columns():
	columns = [
		{
		"fieldname": "name",
		"label": "Gate Pass",
		"fieldtype": "Data",	
		"width": 150
	},{
		"fieldname": "division",
		"label": "Division",
		"fieldtype": "Data",	
		"width": 150
	},{
		"fieldname": "department",
		"label": "Department",
		"fieldtype": "Data",	
		"width": 150
	},
	
	
	{
		"fieldname": "owner",
		"label": "Initiator",
		"fieldtype": "Data",	
		"width": 150
	},
	
	
	{
		"fieldname": "vendor",
		"label": "Vendor",
		"fieldtype": "Data",	
		"width": 150
	},
	{
		"fieldname": "from_date",
		"label": "Date:of Dispatch ",
		"fieldtype": "Date",	
		"width": 150
	},
	{
		"fieldname": "status",
		"label": "Status",
		"fieldtype": "Data",	
		"width": 150
	},
	
	]
	return columns

def get_data(filters):
	# Filters
	
	gatepass_filter={}
	gatepass_filter['Status']=['!=','Draft']

	from_date=datetime.now()
	to_date=datetime.now()
	# getting current user roles
	# get_roles = frappe.get_roles()

	for key in filters:
		if key in ["division","department"]:
			gatepass_filter[key] = filters[key]
			if key == "department" and filters[key] == "All":
				del gatepass_filter["department"]
			
		if key=="from_date":
			from_date=filters[key]
		if key=="to_date":
			to_date=filters[key]
		

	gatepass_filter["from_date"]=['between',[from_date,to_date]]
	# nc_notes=[]
	data=frappe.get_all('Nitta Gate Pass',filters=gatepass_filter,fields=['name','division','department','from_date',
		'owner','vendor','status'])
	
	
	return data

def get_summary(datas):
	
	total_count = len(datas)
	dispatched_count=len([data for data in datas if "dispatched" in data['status'].lower()])
	closed_count = len([data for data in datas if "close" in data['status'].lower()])
	partial_count = len([data for data in datas if "partially completed" in data['status'].lower()])
	rejected_count= len([data for data in datas if "rejected" in data['status'].lower()])
	pending_count = total_count-(closed_count+partial_count+dispatched_count+rejected_count)
	
		
	return [
		{
			'value':total_count,
			'indicator':'Green',
			'label':'Total',
			'datatype':'Int'
		},
		{
			'value':pending_count,
			'indicator':'Yellow',
			'label':'Pending',
			'datatype':'Int'
		},
		{
			'value':rejected_count,
			'indicator':'Red',
			'label':'Rejected',
			'datatype':'Int'
		},
		{
			'value':dispatched_count,
			'indicator':'Green',
			'label':'Dispatched',
			'datatype':'Int'
		},
		# {
		# 	'value':closed_count,
		# 	'indicator':'Red',
		# 	'label':'Closed',
		# 	'datatype':'Int'
		# },
		{
			'value':partial_count,
			
			'indicator':'Blue',
			'label':'Partially Completed',
			'datatype':'Int'
		},
	]

def get_chart(datas):

	print("datas",datas)
	
	#get unique departments
	departments = set()
	
	for data in datas:
		
		if 'department' in data:
			department = data['department']
			print("jhg",department)
			departments.add(department)
	print("department",departments)
	#Get Departments
	departments_data=frappe.get_all("Department",fields=['name'])
	

	#Get department wise approved,pending and rejected
	dispatched=[]
	pending=[]
	rejected=[]
	partial=[]
	close=[]

	department_code=[]
	

	for department in departments:
		rejected_count = len([data for data in datas if data['department'] == department and "rejected" in data['status'].lower()])
		dispatched_count = len([data for data in datas if data['department'] == department and "dispatched" in data['status'].lower()])
		partial_count = len([data for data in datas if data['department']== department and "partially completed" in data['status'].lower()])
		closed_count = len([data for data in datas if data['department'] == department and "close" in data['status'].lower()])
		pending_count = len([data for data in datas if data['department'] == department])-(rejected_count+dispatched_count+partial_count+closed_count)
		dispatched.append(dispatched_count)
		partial.append(partial_count)
		rejected.append(rejected_count)
		close.append(closed_count)
		pending.append(pending_count)


		department_code.append([data for data in departments_data if data.name == department][0].name)

	chart={
		'data':{
			'labels':department_code,
			'datasets':[
				{'name':'Dispatched','values':dispatched},
				{'name':'Rejected','values':rejected},
				{'name':'Pending','values':pending},
				{'name':'Close','values':close},
				{'name':'Partial','values':partial}
				]
		},
		'type':'bar',
		'height':300,
		'colors': ["#00C698","#F25C54","#F7B267"]
	}
	return chart