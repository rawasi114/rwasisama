#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يولّد ملف جدول زمني تجريبي لاختبار استيراد WBS."""
import os
from datetime import date
from openpyxl import Workbook

HERE = os.path.dirname(os.path.abspath(__file__))

ROWS = [
    ("تجهيز الموقع", "التعبئة والأعمال التمهيدية", date(2026, 1, 1), date(2026, 1, 15), 100, ""),
    ("أعمال الحفر", "الأعمال الإنشائية", date(2026, 1, 16), date(2026, 2, 15), 50, ""),
    ("صب الأساسات", "الأعمال الإنشائية", date(2026, 2, 16), date(2026, 3, 15), 0, ""),
    ("أعمال البياض", "أعمال العمارة والتشطيبات", date(2026, 3, 16), date(2026, 4, 30), 0, ""),
    ("تمديدات كهربائية", "الأعمال الكهروميكانيكية", date(2026, 3, 1), date(2026, 4, 15), 0, ""),
    ("التسليم الابتدائي", "الاختبار والتشغيل والتسليم", date(2026, 5, 1), date(2026, 5, 1), 0, "نعم"),
]


def build(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Schedule"
    ws.sheet_view.rightToLeft = True
    ws.append(["النشاط", "المرحلة", "تاريخ البداية", "تاريخ النهاية", "نسبة الإنجاز", "معلم"])
    for r in ROWS:
        ws.append(list(r))
    wb.save(path)
    return len(ROWS)


if __name__ == "__main__":
    n = build(os.path.join(HERE, "schedule_sample.xlsx"))
    print(f"Schedule fixture: {n} activities")
