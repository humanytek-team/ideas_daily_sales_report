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

from odoo import api, models


class DailySalesReport(models.AbstractModel):
    _name = 'report.ideas_daily_sales_report.report_sales'

    @api.model
    def render_html(self, docids, data=None):
        docids = data['ids']
        Report = self.env['report']
        SaleOrder = self.env['sale.order']
        report = Report._get_report_from_name(
            'ideas_daily_sales_report.report_sales')
        docs = SaleOrder.browse(docids)
        tz = self.env.context.get('tz', False)
        if not tz:
            tz = 'US/Arizona'
        datetime_now = datetime.now(timezone(tz))
        data['extra_data'].update({
            'datetime': datetime_now.strftime('%d/%m/%y %H:%M:%S'), })
        docargs = {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': docs,
            'data': data['extra_data'],
        }

        return Report.render('ideas_daily_sales_report.report_sales', docargs)
