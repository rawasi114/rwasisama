# -*- coding: utf-8 -*-
import base64
from io import BytesIO

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    rawasi_stamp_image = fields.Binary(string="ختم الشركة (يُطبع على كل صفحة)")


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    @api.model
    def _rawasi_overlay_stamp(self, pdf_bytes, image_bytes):
        """يضع صورة الختم في أسفل يمين كل صفحة من ملف PDF ويُعيد الناتج."""
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        from odoo.tools.pdf import PdfReader, PdfWriter

        reader = PdfReader(BytesIO(pdf_bytes), strict=False)
        writer = PdfWriter()
        img = ImageReader(BytesIO(image_bytes))
        iw, ih = img.getSize()
        ratio = (ih / iw) if iw else 0.4
        for page in reader.pages:
            pw = float(page.mediabox.width)
            ph = float(page.mediabox.height)
            sw = min(150.0, pw * 0.30)
            sh = sw * ratio
            buf = BytesIO()
            c = canvas.Canvas(buf, pagesize=(pw, ph))
            c.drawImage(
                img, pw - sw - 24, 24, width=sw, height=sh,
                mask="auto", preserveAspectRatio=True,
            )
            c.save()
            buf.seek(0)
            stamp_page = PdfReader(buf, strict=False).pages[0]
            page.merge_page(stamp_page)
            writer.add_page(page)
        out = BytesIO()
        writer.write(out)
        return out.getvalue()

    def _rawasi_company_stamp(self):
        stamp = self.env.company.rawasi_stamp_image
        return base64.b64decode(stamp) if stamp else None

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        pdf, ftype = super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
        if self.env.context.get("rawasi_skip_stamp"):
            return pdf, ftype
        try:
            report = self._get_report(report_ref)
        except Exception:
            report = False
        if report and (report.report_name or "").startswith("rawasi_construction."):
            stamp_bytes = self._rawasi_company_stamp()
            if stamp_bytes:
                try:
                    pdf = self._rawasi_overlay_stamp(pdf, stamp_bytes)
                except Exception:
                    pass
        return pdf, ftype
