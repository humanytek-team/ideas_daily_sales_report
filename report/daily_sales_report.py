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
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class DailySalesReport(models.AbstractModel):
    _name = 'report.daily_sales_report.report_sales'

    @api.model
    def render_html(self, docids, data=None):
        Report = self.env['report']
        SaleOrder = self.env['sale.order']
        report = Report._get_report_from_name(
            'daily_sales_report.report_sales')
        docs = SaleOrder.browse(docids)
        datetime_today = datetime.today()
        data['extra_data'].update(
            {
                'datetime': datetime_today.strftime('%d/%m/%y %H:%M:%S'),
                'date': datetime_today.strftime('%d/%m/%y'),
            })
        docargs = {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': docs,
            'data': data['extra_data'],
        }

        return Report.render('daily_sales_report.report_sales', docargs)
