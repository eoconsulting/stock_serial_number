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
    
    def _get_last_location_ids(self, cr, uid, ids, field_name, arg, context={}):
        obj_location = self.pool.get('stock.location')
        vals = {}
        for serial in self.browse(cr,uid,ids,context=context):
            vals[serial.id] = False
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
                        vals[serial.id] = move.location_dest_id.id
                    elif move.state not in ('cancel','draft'):
                        virtual = move.location_dest_id.id
                    max_date = move_date
                    move_id = move.id
            if not vals[serial.id]: vals[serial.id] = virtual
        return vals

    def _set_last_location_ids(self, cr, uid, ids, field_name, value, arg, context={}):
        for serial_id, loc_id in self._get_last_location_ids(cr, uid, ids, field_name, arg, context=context):
            if loc_id:
                cr.execute("""update stock_serial set last_location_id=%s where id=%s""", (loc_id, serial_id, ))
        return True
    
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
    
    def _last_location_search(self, cr, uid, ids, name, args, context=None):
        if not args:
            return []
        location_obj = self.pool.get('stock.location')
        i = 0
        while i < len(args):
            fargs = args[i][0].split('.', 1)
            if len(fargs) > 1:
                args[i] = (fargs[0], 'in', location_obj.search(cr, uid, [(fargs[1], args[i][1], args[i][2])]))
                i += 1
                continue
            if isinstance(args[i][2], basestring):
                res_ids = location_obj.name_search(cr, uid, args[i][2], [], args[i][1])
                args[i] = (args[i][0], 'in', [x[0] for x in res_ids])
            i += 1
        qu1, qu2 = [], []
        for x in args:
            if x[1] != 'in':
                if (x[2] is False) and (x[1] == '='):
                    qu1.append('(i.id IS NULL)')
                elif (x[2] is False) and (x[1] == '<>' or x[1] == '!='):
                    qu1.append('(i.id IS NOT NULL)')
                else:
                    qu1.append('(i.id %s %s)' % (x[1], '%s'))
                    qu2.append(x[2])
            elif x[1] == 'in':
                if len(x[2]) > 0:
                    qu1.append('(i.id IN (%s))' % (','.join(['%s'] * len(x[2]))))
                    qu2 += x[2]
                else:
                    qu1.append(' (False)')
        if qu1:
            qu1 = ' AND' + ' AND'.join(qu1)
        else:
            qu1 = ''
        cr.execute('SELECT l.id ' \
                'FROM stock_serial l, stock_location i ' \
                'WHERE l.last_location_id = i.id ' + qu1, qu2)
        res = cr.fetchall()
        if not res:
            return [('id', '=', '0')]
        return [('id', 'in', [x[0] for x in res])]


    _name = "stock.serial"
    _columns = {
            'product_id' : fields.many2one('product.product','Product',required=True,select=1, domain=[('is_serial','=',True)]),
            'move_ids' : fields.many2many('stock.move', 'stock_serial_move_rel', 'serial_id','move_id', 'Stock moves', readonly=True),
            'prodlot_id' : fields.many2one('stock.production.lot','Production Lot',select=1),
            'tracking_id' : fields.many2one('stock.tracking','Tracking Number',select=1),
            'name' : fields.char('Serial Number', size=64, required=True),
            'warranty' : fields.float('Warranty time (months)'),
            'warranty_start' : fields.date('Warranty Start'),
            'warranty_end' : fields.function(_get_warranty_end,string='Warranty End',type="date",method=True),
            'last_location_id' : fields.function(_get_last_location_ids, fnct_inv=_set_last_location_ids,
                                                 string='Last Location',fnct_search=_last_location_search,
                                                 type="many2one",relation="stock.location",method=True,select=True,store=True),
            'uom_id' : fields.related('product_id','uom_id',type='many2one',relation='product.uom',string='Unit of Measure', store=True, readonly=True),
        }

    _defaults = {
            'warranty_start' : lambda *a: datetime.now().strftime('%Y-%m-%d'),
            'product_id' : lambda s,cr,u,c: c.get('product_id',False),
            'prodlot_id' : lambda s,cr,u,c: c.get('prodlot_id',False),
            'tracking_id' : lambda s,cr,u,c: c.get('tracking_id',False),
            'name' : lambda s,cr,u,c: c.get('product_id',False) and s.pool.get('product.product').browse(cr,u,c.get('product_id')).serial_sequence_id and s.pool.get("ir.sequence").get_id(cr,u,s.pool.get('product.product').browse(cr,u,c.get('product_id')).serial_sequence_id.id) or False,
        }

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
            product = self.pool.get('product.product').browse(cr, uid, context['product_id'])
            try:
                if product.product_tmpl_id.is_multi_variants:
                    args.append(('product_id.product_tmpl_id.id', '=', product.product_tmpl_id.id))
                else:
                    args.append(('product_id', '=', context['product_id']))
            except:
                # If 'product_variant_multi' module is not installed, the field 'is_multi_variants'
                # not exist, so an exception is raised
                args.append(('product_id', '=', context['product_id']))
        res = super(stock_serial, self).search(cr, uid, args, offset=offset, limit=limit, order=order,
                                                                 context=context, count=count)
        return res
        
stock_serial()
