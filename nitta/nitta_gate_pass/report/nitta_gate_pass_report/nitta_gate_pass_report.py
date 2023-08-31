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
		"fieldname": "work_to_be_done",
		"label": "Work To be done",
		"fieldtype": "Data",	
		"width": 150
	},{
		"fieldname": "vendor",
		"label": "Vendor",
		"fieldtype": "Data",	
		"width": 150
	},{
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

	department = filters['department']
	report_status=filters['report_status']
	division = filters['division']
	if(division=='All'):
		division=''
	if(department=="All"):
		department=''
	if(report_status=="All"):
		report_status=''

	from_date=datetime(2000,1,1,0,0,0)
	if 'from_date' in filters:
		from_date=filters["from_date"]
		from_date = datetime.strptime(from_date,'%Y-%m-%d')
		from_date = from_date.strftime('%Y-%m-%d')
		
	to_date=datetime(2000,1,1,0,0,0)
	if 'to_date' in filters:
		to_date=filters["to_date"]
		to_date = datetime.strptime(to_date,'%Y-%m-%d')
		to_date = to_date.strftime('%Y-%m-%d')



	gate_pass_details =frappe.db.sql("""
		select gate_pass.name,gate_pass.division,gate_pass.department,
		gate_pass.owner,gate_pass.vendor,gate_pass.status ,item.pdt_name as item,item.quantity,item.work_to_be_done,item.expected_delivery_date
		
		from `tabNitta Gate Pass` gate_pass
		left join `tabNitta item` item on gate_pass.name=item.parent  where (gate_pass.from_date BETWEEN %(from_date)s AND %(to_date)s)
        AND (gate_pass.department = %(department)s OR %(department)s = '')
        AND (gate_pass.division = %(division)s OR %(division)s = '') 
		AND (gate_pass.status=%(status)s OR %(status)s='') 
		
	""",values={'from_date':from_date,'to_date':to_date,'department':department,'division':division,'status':report_status},as_dict=1)
	
	for gate_pass in gate_pass_details:
		data.append({
			'division':gate_pass.division,
			'department':gate_pass.department,
			'gate_pass':gate_pass.name,
			'initiator':gate_pass.owner,
			'product':gate_pass.item,
			'status':gate_pass.status,
			'quantity':gate_pass.quantity,
			'work_to_be_done':gate_pass.work_to_be_done,
			'expected_delivery_date':gate_pass.expected_delivery_date,
			'vendor':gate_pass.vendor,
			

		})
	
	return data
