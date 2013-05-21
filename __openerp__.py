# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
# Copyright (c) 2011-2013 Cubic ERP - Teradata SAC. (http://cubicerp.com).
#                         Mariano Ruiz (Enterprise Objects Consulting)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    "name": "Stock and Production Serial Number",
    "version": "1.3",
    "description": """
Adds unique serial numbers to the production lots and stock moves.
    """,
    "author": "Cubic ERP / Modified by Enterprise Objects Consulting",
    "website": "http://www.eoconsulting.com.ar",
    "category": "Warehouse",
    "depends": [
        "stock",
        "partner_address_name_search",
	],
    "update_xml":[
	    "stock_view.xml",
	    "product_view.xml",
	    "stock_serial_number_view.xml",
	    "stock_serial_number.xml",
	],
    "data": [
        'security/ir.model.access.csv',
	],
    "installable": True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
