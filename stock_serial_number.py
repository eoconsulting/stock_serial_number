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


from osv import osv, fields
from datetime import datetime
from dateutil.relativedelta import relativedelta

class stock_serial(osv.osv):
    
    def _get_last_move(self, cr, uid, ids, field_name, arg, context={}):
        vals = {}
        for serial in self.browse(cr,uid,ids,context=context):
            vals[serial.id] = {'last_location_id': False, 'last_state': False, 'last_address_id': False}
            virtual = False
            max_date = datetime(1,1,1)
            for move in serial.move_ids:
                move_date = datetime.strptime(move.date,'%Y-%m-%d %H:%M:%S')
                move_id = move.id
                if move_date >= max_date:
                    if move_date == max_date and move.id > move_id:
                        # NOTE: Date fields only save in seconds precisions,
                        # when a operation throws 2 moves, both operations have
                        # the same date time, so the last move only can only know
                        # by the pkid
                        break
                    if move.state == 'done':
                        vals[serial.id]['last_location_id'] = move.location_dest_id.id
                        vals[serial.id]['last_state'] = move.state
                        vals[serial.id]['last_address_id'] = move.address_id.id
                    elif move.state not in ('cancel','draft'):
                        virtual = move
                    max_date = move_date
                    move_id = move.id
            if not vals[serial.id]:
                vals[serial.id]['last_location_id'] = virtual.location_dest_id.id
                vals[serial.id]['last_state'] = virtual.state
                vals[serial.id]['last_address_id'] = virtual.address_id.id
        return vals
    
    def _get_warranty_end(self, cr, uid, ids, field_name, arg, context=None):
        if context is None: context = {}
        vals = {}
        for serial in self.browse(cr,uid,ids,context=context):
            if serial.warranty_start:
                start = serial.warranty_start
                warranty = serial.warranty
                vals[serial.id] = self.get_warranty_end(start,warranty)
            else:
                vals[serial.id] = False
        return vals

    def _last_location_search(self, cr, uid, obj, field_name, args, context={}):
        ids = []
        if not len(args):
            [('id', 'in', ids)]
        operator = args[0][1]
        value = args[0][2]
        if operator not in ['=', '!=', 'ilike', 'not ilike']:
            return [('id', 'in', ids)]
        cr.execute('select id from stock_serial')
        move_ids = self._get_last_move(cr, uid, map(lambda x: x[0], cr.fetchall()), field_name, None, context)
        for res_id in move_ids.keys():
            location_id = move_ids[res_id]['last_location_id']
            if operator == '=':
                if value == location_id:
                    ids.append(res_id)
            elif operator == '!=':
                if value != location_id:
                    ids.append(res_id)
            elif operator == 'ilike' and location_id:
                if value.lower() in self.pool.get('stock.location').read(cr,uid,location_id,['name'],context=context)['name'].lower():
                    ids.append(res_id)
            elif operator == 'not ilike':
                if not location_id or value.lower() not in self.pool.get('stock.location').read(cr,uid,location_id,['name'],context=context)['name'].lower():
                    ids.append(res_id)
        return [('id', 'in', ids)]

    def _last_state_search(self, cr, uid, obj, field_name, args, context={}):
        ids = []
        if not len(args):
            [('id', 'in', ids)]
        operator = args[0][1]
        value = args[0][2]
        if operator not in ['=', '!=']:
            return [('id', 'in', ids)]
        cr.execute('select id from stock_serial')
        move_ids = self._get_last_move(cr, uid, map(lambda x: x[0], cr.fetchall()), field_name, None, context)
        for res_id in move_ids.keys():
            state = move_ids[res_id]['last_state']
            if operator == '=':
                if value == state:
                    ids.append(res_id)
            elif operator == '!=':
                if value != state:
                    ids.append(res_id)
        return [('id', 'in', ids)]

    _name = "stock.serial"
    _columns = {
            'product_id' : fields.many2one('product.product','Product',required=True,select=1, domain=[('is_serial','=',True)]),
            'move_ids' : fields.many2many('stock.move', 'stock_serial_move_rel', 'serial_id','move_id', 'Stock moves', readonly=True),
            'prodlot_id' : fields.many2one('stock.production.lot','Production Lot',select=1),
            'tracking_id' : fields.many2one('stock.tracking','Tracking Number',select=1),
            'name' : fields.char('Serial Number', size=64, required=True),
            'note': fields.text("Notes"),
            'warranty' : fields.float('Warranty time (months)'),
            'warranty_start' : fields.date('Warranty Start'),
            'warranty_end' : fields.function(_get_warranty_end,string='Warranty End',type="date",method=True),
            'last_location_id' : fields.function(_get_last_move,string='Last Location',fnct_search=_last_location_search,
                                                 type="many2one",relation="stock.location",
                                                 method=True,select=True,multi=True),
            'last_state' : fields.function(_get_last_move,string='Last State',fnct_search=_last_state_search,
                                                 type="selection",selection=[('draft', 'New'), ('waiting', 'Waiting Another Move'), ('confirmed', 'Waiting Availability'), ('assigned', 'Available'), ('done', 'Done'), ('cancel', 'Cancelled')],
                                                 method=True,select=True,multi=True),
            'last_address_id' : fields.function(_get_last_move,string='Last Destination Address',
                                                type="many2one",relation="res.partner.address",
                                                method=True,multi=True),
            'uom_id' : fields.related('product_id','uom_id',type='many2one',relation='product.uom',string='Unit of Measure', store=True, readonly=True),
        }

    _defaults = {
            'warranty_start' : lambda *a: datetime.now().strftime('%Y-%m-%d'),
            'product_id' : lambda s,cr,u,c: c.get('product_id',False),
            'prodlot_id' : lambda s,cr,u,c: c.get('prodlot_id',False),
            'tracking_id' : lambda s,cr,u,c: c.get('tracking_id',False),
            'name' : lambda s,cr,u,c: c.get('product_id',False) and s.pool.get('product.product').browse(cr,u,c.get('product_id')).serial_sequence_id and s.pool.get("ir.sequence").get_id(cr,u,s.pool.get('product.product').browse(cr,u,c.get('product_id')).serial_sequence_id.id) or False,
        }

    _order = "name desc"

    def on_change_product_id(self, cr, uid, ids, prod_id=False, context=None):
        if not prod_id:
            return {}

        product = self.pool.get('product.product').browse(cr, uid, prod_id, context=context)
        warranty  = product.warranty
        start = datetime.now().strftime('%Y-%m-%d')
        
        result = {
            #'prodlot_id': False,
            'warranty': warranty,
            #'move_ids': False,
            'warranty_start' : start,
            'warranty_end': self.get_warranty_end(start,warranty),
        }
        return {'value': result}
    
    def on_change_warranty(self, cr, uid, ids, start, warranty, context=None):
        if not start:
            return {}
        
        result = {
            'warranty_end': self.get_warranty_end(start,warranty),
        }
        return {'value': result}

    def get_warranty_end(self,start,months):
        if not start: return False
        limit = datetime.strptime(start,'%Y-%m-%d') + relativedelta(months=int(months))
        return limit.strftime('%Y-%m-%d')

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):
        if context.get('last_location_id', False):
            args.append('|')
            args.append(('last_location_id', '=', context['last_location_id']))
            args.append(('last_location_id', '=', False))
        if context.get('product_id', False):
            try:
                if context.get('move_id', False):
                    move = self.pool.get('stock.move').browse(cr,uid,context['move_id'])
                    if move.production_id:
                        product = self.pool.get('product.product').browse(cr, uid, context['product_id'])
                        if product.product_tmpl_id.is_multi_variants:
                            args.append(('product_id.product_tmpl_id.id', '=', product.product_tmpl_id.id))
                        else:
                            args.append(('product_id', '=', context['product_id']))
                    else:
                        args.append(('product_id', '=', context['product_id']))
                else:
                    args.append(('product_id', '=', context['product_id']))
            except AttributeError:
                # If 'product_variant_multi' or 'mrp' modules are not installed,
                # the fields 'is_multi_variants' and 'production_id'
                # not exist, so an exception is raised when try to access them
                args.append(('product_id', '=', context['product_id']))
        res = super(stock_serial, self).search(cr, uid, args, offset=offset, limit=limit, order=order,
                                                                 context=context, count=count)
        return res
        
stock_serial()
