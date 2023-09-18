# Copyright (c) 2023, Ideenkreise and contributors
# For license information, please see license.txt

import frappe
from datetime import date,datetime,timedelta


def execute(filters=None):
	columns, data = [], []
	columns=get_column()
	data =get_data(filters)
	return columns, data

def get_column():
	
	return [
		{
		"fieldname": "gate_pass",
		"label": "gate Pass",
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
		"fieldname": "initiator",
		"label": "Initiator",
		"fieldtype": "Data",	
		"width": 150
	},{
		"fieldname": "product",
		"label": "Product",
		"fieldtype": "Data",	
		"width": 150
	},
	{
		"fieldname": "quantity",
		"label": "Quantity",
		"fieldtype": "Data",	
		"width": 150
	},
	{
		"fieldname": "remaining",
		"label": "Remaining Quantity",
		"fieldtype": "Data",	
		"width": 150
	},
	{
		"fieldname": "work_to_be_done",
		"label": "Work To be done",
		"fieldtype": "Data",	
		"width": 150
	},{
		"fieldname": "vendor",
		"label": "Vendor",
		"fieldtype": "Data",	
		"width": 150
	},
	{
		"fieldname": "dispatched_date",
		"label": "Date:of Dispatch ",
		"fieldtype": "Date",	
		"width": 150
	},
	{
		"fieldname": "expected_delivery_date",
		"label": "Expected Delivery Date ",
		"fieldtype": "Date",	
		"width": 150
	},{
		"fieldname": "status",
		"label": "Status",
		"fieldtype": "Data",	
		"width": 150
	},
	


	]

def get_data(filters):

	
	data=[]
	gatepass_filter={}
	gatepass_filter['status']=['!=','Draft']

	from_date=datetime.now()
	to_date=datetime.now()
	# getting current user roles
	# get_roles = frappe.get_roles()

	for key in filters:
		if key in ["division","department","status"]:
			gatepass_filter[key] = filters[key]
			if key == "department" and filters[key] == "All" :
				del gatepass_filter["department"]
			if key == "status" and filters[key] == "All" :
				del gatepass_filter["status"]

			
		if key=="from_date":
			from_date=filters[key]
		if key=="to_date":
			to_date=filters[key]
	gatepass_filter["from_date"]=['between',[from_date,to_date]]
	print("filter",gatepass_filter)
	gate_pass=frappe.get_all('Nitta Gate Pass',filters=gatepass_filter,fields=['name','department','division','vendor','from_date','owner','status'])
	
	for item in gate_pass:
		if not item['status']=="Draft":
		
			gate_pass_item=frappe.get_all('Nitta item',filters={'parent':item['name']},
			fields=['pdt_name','work_to_be_done','expected_delivery_date','remaining','quantity','status'])
		
			for d in gate_pass_item:
				data.append({
					'division':item['division'],
					'department':item['department'],
					'gate_pass':item['name'],
					'initiator':item['owner'],
					'product':d['pdt_name'],
					'status':item['status'],
					'quantity':d['quantity'],
					'work_to_be_done':d['work_to_be_done'],
					'expected_delivery_date':d['expected_delivery_date'],
					'vendor':item['vendor'],
					'dispatched_date':item['from_date'],
					'remaining':d['remaining']

				})
	return data
