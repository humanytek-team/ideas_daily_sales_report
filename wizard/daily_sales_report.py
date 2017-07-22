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

from datetime import datetime
from pytz import timezone

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

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
    date = fields.Date(
        string='Date',
        required=True,
        default=datetime.today().strftime('%Y-%m-%d'))

    @api.model
    def _get_invoice_and_payments_by_pay_method(
            self, invoices, pay_methods_ids):

        invoices_by_pay_method_id = dict()
        payments_by_pay_method_id = dict()

        for pay_method_id in pay_methods_ids:
            invoices_by_pay_method_id[pay_method_id] = list()
            payments_by_pay_method_id[pay_method_id] = list()
            invoices_by_pay_method = \
                invoices.filtered(
                    lambda inv: int(pay_method_id) in
                    inv.pay_method_ids.mapped('id'))

            for invoice in invoices_by_pay_method:
                customer_name = \
                    invoice.partner_id.name.upper()

                invoices_by_pay_method_id[pay_method_id].append(
                    {
                        'move_name': invoice.move_name,
                        'origin': invoice.origin,
                        'customer': customer_name,
                        'amount_total': invoice.amount_total,
                        'state': invoice.state,
                        'state_label': INVOICE_STATES[invoice.state],
                    }
                )

                if invoice.payment_ids:
                    for payment in invoice.payment_ids:
                        if payment.cmpl_type != 'payment':
                            payment_method_name = payment.cmpl_type
                        else:
                            payment_method_name = \
                                payment.other_payment.name

                        invoices_names_list = [
                            inv.move_name for inv in payment.invoice_ids]
                        invoices_names = ', '.join(invoices_names_list)

                        payments_by_pay_method_id[pay_method_id].append({
                            'name': payment.name,
                            'invoices_names': invoices_names,
                            'customer': customer_name,
                            'payment_method_name': payment_method_name,
                            'amount': payment.amount,
                            })

        invoices_and_payments = dict()
        invoices_and_payments['invoices_by_pay_method_id'] = \
            invoices_by_pay_method_id
        invoices_and_payments['payments_by_pay_method_id'] = \
            payments_by_pay_method_id

        return invoices_and_payments

    @api.model
    def _get_date_to_user_timezone(self, datetime_to_convert):
        """Returns the datetime received converted to a date set to
        timezone of user"""

        tz = self.env.context.get('tz', False)
        if not tz:
            tz = 'US/Arizona'

        datetime_now_with_tz = datetime.now(timezone(tz))
        utc_difference_timedelta = datetime_now_with_tz.utcoffset()
        datetime_to_convert = datetime.strptime(
            datetime_to_convert, '%Y-%m-%d %H:%M:%S')
        datetime_result = datetime_to_convert + utc_difference_timedelta
        date_result = datetime_result.strftime('%Y-%m-%d')

        return date_result

    @api.multi
    def print_daily_sales_report(self):
        """Print report Daily Sales Report"""

        self.ensure_one()
        wizard_data = self.read(['warehouse_id', 'date'])[0]
        SaleOrder = self.env['sale.order']
        all_sale_orders = SaleOrder.search([
            ('state', '=', 'sale'),
            ('warehouse_id', '=', wizard_data['warehouse_id'][0]),
            ], order='date_order')

        sale_orders = all_sale_orders.filtered(
            lambda so:
            self._get_date_to_user_timezone(so.date_order) <=
            wizard_data['date'] and
            self._get_date_to_user_timezone(so.date_order) >=
            wizard_data['date']
        )

        if sale_orders:

            so_invoices = sale_orders.mapped('invoice_ids').filtered(
                lambda inv: inv.type == 'out_invoice' and
                inv.date_invoice == wizard_data['date'] and
                inv.state != 'cancel'
            )

            sale_orders_invoices_cancelled = sale_orders.mapped('invoice_ids')\
                .filtered(
                    lambda inv: inv.type == 'out_invoice' and
                    inv.date_invoice == wizard_data['date'] and
                    inv.state == 'cancel'
                    )

            if not so_invoices and \
                    not sale_orders_invoices_cancelled:
                raise ValidationError(
                    _('No sales for the warehouse and day selected'))

            data = dict()
            data['ids'] = sale_orders.filtered(
                lambda so: so.invoice_ids and
                so.mapped('invoice_ids').filtered(
                    lambda inv: inv.type == 'out_invoice' and
                    inv.date_invoice == wizard_data['date']
                )
            ).mapped('id')

            extra_data = dict()

            date_split = wizard_data['date'].split('-')
            extra_data['date'] = '{0}/{1}/{2}'.format(
                date_split[2], date_split[1], date_split[0])

            so_invoices_no_credit_no_cancelled = sale_orders \
                .mapped('invoice_ids') \
                .filtered(
                    lambda inv: inv.type == 'out_invoice' and
                    inv.date_invoice == wizard_data['date'] and
                    inv.state != 'cancel' and
                    inv.date_due == inv.date_invoice
                    )

            sale_orders_invoices_with_credit = sale_orders.mapped(
                'invoice_ids').filtered(
                    lambda inv: inv.type == 'out_invoice' and
                    inv.date_invoice == wizard_data['date'] and
                    inv.state != 'cancel' and
                    inv.date_due > inv.date_invoice
                    )

            sale_orders_invoices_out_refund = sale_orders \
                .mapped('invoice_ids') \
                .filtered(
                    lambda inv: inv.type == 'out_refund' and
                    inv.date_invoice == wizard_data['date'] and
                    inv.state != 'cancel'
                    )

            sales_total_with_customer_refund = sum(
                so_invoices.mapped('amount_total'))

            total_customer_refund = sum(
                sale_orders_invoices_out_refund.mapped('amount_total')
            )

            sales_total = sales_total_with_customer_refund - \
                total_customer_refund

            extra_data['sales_total'] = sales_total

            payments_done = so_invoices.mapped('payment_ids') \
                .filtered(
                        lambda pay: pay.payment_type == 'inbound' and
                        pay.payment_date == wizard_data['date']
                    )

            payments_done_total = sum(payments_done.mapped('amount'))

            extra_data['payments_done_total'] = payments_done_total

            PayMethod = self.env['pay.method']
            pay_methods_all = PayMethod.search([])

            pay_methods = so_invoices.mapped('pay_method_ids')
            pay_methods_ids = [
                str(pay_method_id) for pay_method_id
                in pay_methods.mapped('id')]
            extra_data['pay_methods_ids'] = pay_methods_ids

            pay_methods_invoices_no_credit = \
                so_invoices_no_credit_no_cancelled.mapped('pay_method_ids')
            pay_methods_ids_invoices_no_credit = [
                str(pay_method_id) for pay_method_id
                in pay_methods_invoices_no_credit.mapped('id')]
            extra_data['pay_methods_ids_invoices_no_credit'] = \
                pay_methods_ids_invoices_no_credit

            total_invoices_by_pay_method_id = dict()
            for pay_method in pay_methods:
                total_invoices_by_pay_method_id[pay_method.id] = \
                    sum(so_invoices.filtered(
                        lambda inv: pay_method in inv.pay_method_ids).mapped(
                            'amount_total'))

            extra_data['total_invoices_by_pay_method_id'] = \
                total_invoices_by_pay_method_id

            total_invoices_no_credit_by_pay_method_id = dict()
            for pay_method in pay_methods_invoices_no_credit:
                total_invoices_no_credit_by_pay_method_id[pay_method.id] = \
                    sum(so_invoices_no_credit_no_cancelled.filtered(
                        lambda inv: pay_method in inv.pay_method_ids).mapped(
                            'amount_total'))

            extra_data['total_invoices_no_credit_by_pay_method_id'] = \
                total_invoices_no_credit_by_pay_method_id

            pay_methods_names_by_id = {
                str(pay_method.id): pay_method.name
                for pay_method in pay_methods_all}
            extra_data['pay_methods_names_by_id'] = pay_methods_names_by_id

            invoices_and_payments_no_credit = \
                self._get_invoice_and_payments_by_pay_method(
                    so_invoices_no_credit_no_cancelled,
                    pay_methods_ids_invoices_no_credit)

            extra_data['invoices_no_credit_by_pay_method_id'] = \
                invoices_and_payments_no_credit['invoices_by_pay_method_id']
            extra_data['payments_no_credit_by_pay_method_id'] = \
                invoices_and_payments_no_credit['payments_by_pay_method_id']

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

            extra_data['total_customer_refund'] = total_customer_refund

            sales_total_plus_customer_refund = sales_total + \
                total_customer_refund
            extra_data['sales_total_plus_customer_refund'] = \
                sales_total_plus_customer_refund

            count_sale_orders_invoices = len(so_invoices)
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
                    len(so_invoices.filtered(
                        lambda inv: pay_method in inv.pay_method_ids))

            extra_data['count_total_invoices_by_pay_method_id'] = \
                count_total_invoices_by_pay_method_id

            sale_orders_invoices_cancelled_data = list()

            for invoice in sale_orders_invoices_cancelled:
                invoice_data = dict()
                invoice_data = {
                    'move_name': invoice.move_name,
                    'origin': invoice.origin,
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

            sale_orders_invoices_with_credit_data = list()
            for invoice in sale_orders_invoices_with_credit:
                customer_name = \
                    invoice.partner_id.name.upper()
                sale_orders_invoices_with_credit_data.append(
                    {
                        'move_name': invoice.move_name,
                        'origin': invoice.origin,
                        'customer': customer_name,
                        'amount_total': invoice.amount_total,
                        'state': invoice.state,
                        'state_label': INVOICE_STATES[invoice.state],
                    }
                )
            extra_data['sale_orders_invoices_with_credit_data'] = \
                sale_orders_invoices_with_credit_data

            total_payments_no_credit_by_pay_method_id = dict()
            for pay_method in pay_methods_invoices_no_credit:
                total_payments_no_credit_by_pay_method_id[pay_method.id] = \
                    sum(so_invoices_no_credit_no_cancelled
                        .filtered(
                            lambda inv: pay_method in inv.pay_method_ids
                            )
                        .mapped('payment_ids')
                        .mapped('amount'))
            extra_data['total_payments_no_credit_by_pay_method_id'] = \
                total_payments_no_credit_by_pay_method_id

            data['extra_data'] = extra_data

            Report = self.env['report']
            return Report.get_action(
                self,
                'ideas_daily_sales_report.report_sales',
                data=data)
        else:
            raise ValidationError(
                _('No sales for the warehouse and day selected'))
