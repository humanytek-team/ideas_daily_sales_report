# -*- coding: utf-8 -*-
###############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2017 Humanytek (<www.humanytek.com>).
#    Manuel Márquez <manuel@humanytek.com>
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
###############################################################################

import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

INVOICE_STATES = {
    'draft': _('Draft'),
    'proforma': _('Pro-forma'),
    'proforma2': _('Pro-forma'),
    'open': _('Open'),
    'paid': _('Paid'),
    'cancel': _('Cancelled'),
    }


class DailySalesReport(models.TransientModel):
    _name = "daily.sales.report"
    _description = "Daily Sales Report"

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        required=True)
    date = fields.Date(string='Date', required=True)

    @api.multi
    def print_daily_sales_report(self):
        """Print report Daily Sales Report"""

        self.ensure_one()
        wizard_data = self.read(['warehouse_id', 'date'])[0]
        SaleOrder = self.env['sale.order']
        sale_orders = SaleOrder.search([
            ('state', '=', 'sale'),
            ('date_order', '<=', wizard_data['date']),
            ('date_order', '>=', wizard_data['date']),
            ('warehouse_id', '=', wizard_data['warehouse_id'][0]),
            ])

        if sale_orders:
            data = dict()
            data['ids'] = sale_orders.mapped('id')
            extra_data = dict()

            sale_orders_invoices = sale_orders.mapped('invoice_ids').filtered(
                lambda inv: inv.type == 'out_invoice' and
                inv.date_invoice == wizard_data['date'] and
                inv.state != 'cancel'
            )

            sales_total = sum(
                sale_orders_invoices.mapped('amount_total'))
            extra_data['sales_total'] = sales_total

            payments_done = sale_orders_invoices.mapped(
                    'payment_ids').filtered(
                        lambda pay: pay.payment_type == 'inbound' and
                        pay.payment_date == wizard_data['date']
                    )
            payments_done_total = sum(payments_done.mapped('amount'))
            extra_data['payments_done_total'] = payments_done_total

            pay_methods = sale_orders_invoices.mapped('pay_method_ids')
            pay_methods_ids = [
                str(pay_method_id) for pay_method_id
                in pay_methods.mapped('id')]
            extra_data['pay_methods_ids'] = pay_methods_ids

            total_invoices_by_pay_method_id = dict()
            for pay_method in pay_methods:
                total_invoices_by_pay_method_id[pay_method.id] = \
                    sum(sale_orders_invoices.filtered(
                        lambda inv: pay_method in inv.pay_method_ids).mapped(
                            'amount_total'))

            extra_data['total_invoices_by_pay_method_id'] = \
                total_invoices_by_pay_method_id

            pay_methods_names_by_id = {
                str(pay_method.id): pay_method.name
                for pay_method in pay_methods}
            extra_data['pay_methods_names_by_id'] = pay_methods_names_by_id

            invoices_by_pay_method_id = dict()
            for pay_method_id in pay_methods_ids:
                invoices_by_pay_method_id[pay_method_id] = list()
                sale_orders_invoices_by_pay_method = \
                    sale_orders_invoices.filtered(
                        lambda inv: int(pay_method_id) in
                        inv.pay_method_ids.mapped('id'))

                for sale_order_invoice in sale_orders_invoices_by_pay_method:
                    customer_name = \
                        sale_order_invoice.partner_id.name.upper()
                    invoices_by_pay_method_id[pay_method_id].append(
                        {
                            'move_name': sale_order_invoice.move_name,
                            'customer': customer_name,
                            'amount_total': sale_order_invoice.amount_total,
                            'state': sale_order_invoice.state,
                            'state_label': INVOICE_STATES[
                                sale_order_invoice.state],
                        }
                    )
            extra_data['invoices_by_pay_method_id'] = invoices_by_pay_method_id

            sale_orders_invoices_with_credit = sale_orders_invoices.filtered(
                lambda inv: inv.date_due > inv.date_invoice
            )

            credit_total = sum(
                sale_orders_invoices_with_credit.mapped('amount_total'))
            extra_data['credit_total'] = credit_total

            total_invoices_credit_by_pay_method_id = dict()
            for pay_method in pay_methods:
                total_invoices_credit_by_pay_method_id[pay_method.id] = \
                    sum(sale_orders_invoices_with_credit.filtered(
                        lambda inv: pay_method in inv.pay_method_ids).mapped(
                            'amount_total'))
            extra_data['total_invoices_credit_by_pay_method_id'] = \
                total_invoices_credit_by_pay_method_id

            sale_orders_invoices_out_refund = sale_orders \
                .mapped('invoice_ids') \
                .filtered(
                    lambda inv: inv.type == 'out_refund' and
                    inv.date_invoice == wizard_data['date']
                    )
            total_customer_refund = sum(
                sale_orders_invoices_out_refund.mapped('amount_total')
            )
            extra_data['total_customer_refund'] = total_customer_refund

            sales_total_minus_customer_refund = sales_total - \
                total_customer_refund
            extra_data['sales_total_minus_customer_refund'] = \
                sales_total_minus_customer_refund

            count_sale_orders_invoices = len(sale_orders_invoices)
            count_sale_orders_invoices_out_refund = len(
                sale_orders_invoices_out_refund)
            count_total_sale_orders_invoices = count_sale_orders_invoices + \
                count_sale_orders_invoices_out_refund
            extra_data['count_sale_orders_invoices_out_refund'] = \
                count_sale_orders_invoices_out_refund
            extra_data['count_total_sale_orders_invoices'] = \
                count_total_sale_orders_invoices

            count_total_invoices_by_pay_method_id = dict()
            for pay_method in pay_methods:
                count_total_invoices_by_pay_method_id[pay_method.id] = \
                    len(sale_orders_invoices.filtered(
                        lambda inv: pay_method in inv.pay_method_ids))

            extra_data['count_total_invoices_by_pay_method_id'] = \
                count_total_invoices_by_pay_method_id

            sale_orders_invoices_cancelled = sale_orders.mapped('invoice_ids')\
                .filtered(
                    lambda inv: inv.type == 'out_invoice' and
                    inv.date_invoice == wizard_data['date'] and
                    inv.state == 'cancel'
                    )

            sale_orders_invoices_cancelled_data = list()

            for invoice in sale_orders_invoices_cancelled:
                invoice_data = dict()
                invoice_data = {
                    'move_name': invoice.move_name,
                    'customer': invoice.partner_id.name,
                }
                if invoice.date_due > invoice.date_invoice:
                    invoice_data.update({
                        'credit': invoice.amount_total,
                        'debit': ''
                    })
                else:
                    invoice_data.update({
                        'debit': invoice.amount_total,
                        'credit': ''
                    })
                sale_orders_invoices_cancelled_data.append(
                    invoice_data
                )

            extra_data['sale_orders_invoices_cancelled_data'] = \
                sale_orders_invoices_cancelled_data

            total_sale_orders_invoices_cancelled = \
                sum(sale_orders_invoices_cancelled.mapped('amount_total'))
            extra_data['total_sale_orders_invoices_cancelled'] = \
                total_sale_orders_invoices_cancelled

            total_invoices_cancelled_with_credit = \
                sum(sale_orders_invoices_cancelled.filtered(
                    lambda inv: inv.date_due > inv.date_invoice
                    ).mapped('amount_total'))
            extra_data['total_invoices_cancelled_with_credit'] = \
                total_invoices_cancelled_with_credit

            total_invoices_cancelled_no_credit = \
                sum(sale_orders_invoices_cancelled.filtered(
                    lambda inv: inv.date_due == inv.date_invoice
                    ).mapped('amount_total'))
            extra_data['total_invoices_cancelled_no_credit'] = \
                total_invoices_cancelled_no_credit

            data['extra_data'] = extra_data

            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'daily_sales_report.report_sales',
                'datas': data,
                }
        else:
            raise ValidationError(
                _('No sales for the warehouse and day selected'))
