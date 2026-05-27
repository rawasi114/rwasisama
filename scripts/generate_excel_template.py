"""Generate the standard Excel import template used by the data-entry team.

Usage:
    python -m scripts.generate_excel_template [output_path]

Output defaults to ``seed_data/excel_import_template.xlsx``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

HEADER_FILL = PatternFill(start_color="253747", end_color="253747", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True, name="DIN Next LT Arabic")


TENDERS_HEADERS = [
    ("etimad_id", "رقم المنافسة في اعتماد", "إلزامي"),
    ("title_ar", "عنوان المنافسة", "إلزامي"),
    ("government_entity_code", "كود الجهة الحكومية", "إلزامي (راجع ورقة Codes)"),
    ("sub_entity_name", "الجهة الفرعية", "اختياري"),
    ("region_code", "كود المنطقة", "اختياري"),
    ("city_code", "كود المدينة", "اختياري"),
    ("sector_code", "كود القطاع", "اختياري"),
    ("award_date", "تاريخ الترسية (YYYY-MM-DD)", "إلزامي"),
    ("award_value", "قيمة الترسية بالريال", "إلزامي"),
    ("winner_name", "اسم الفائز", "إلزامي"),
    ("total_bidders", "عدد المتنافسين", "اختياري"),
    ("rawasi_participated", "هل دخلت رواسي؟ (TRUE/FALSE)", "إلزامي"),
    ("rawasi_bid_amount", "قيمة عرض رواسي", "إن دخلت"),
    ("rawasi_rank", "رتبة رواسي", "إن دخلت"),
    ("boq_filename", "اسم ملف جدول الكميات", "اختياري"),
    ("notes", "ملاحظات", "اختياري"),
]


BIDDERS_HEADERS = [
    ("tender_etimad_id", "رقم المنافسة"),
    ("bidder_name", "اسم المتنافس"),
    ("bid_amount", "قيمة العرض"),
    ("rank", "الترتيب"),
]


def build_template() -> Workbook:
    wb = Workbook()

    # Sheet 1: Tenders_Master
    ws = wb.active
    ws.title = "Tenders_Master"
    for col_idx, (col_name, _, _) in enumerate(TENDERS_HEADERS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[cell.column_letter].width = max(20, len(col_name) + 4)

    # Sample row
    ws.append(
        [
            "40-2026م",
            "توريد أثاث مكتبي للمبنى الجديد",
            "NG",
            "إدارة المباني",
            "EP",
            "DAM",
            "FURN-OFFICE",
            "2026-05-15",
            2_847_500.00,
            "شركة الديار للأثاث",
            7,
            False,
            "",
            "",
            "boq_40-2026.xlsx",
            "",
        ]
    )

    # Sheet 2: Bidders_Detail
    ws2 = wb.create_sheet("Bidders_Detail")
    for col_idx, (col_name, _) in enumerate(BIDDERS_HEADERS, start=1):
        cell = ws2.cell(row=1, column=col_idx, value=col_name)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        ws2.column_dimensions[cell.column_letter].width = 25

    # Sheet 3: Instructions
    instructions = wb.create_sheet("Instructions")
    instructions.append(["دليل استخدام القالب"])
    instructions["A1"].font = Font(bold=True, size=14)
    rows = [
        [""],
        ["1. كل صف في ورقة Tenders_Master يمثل ترسية واحدة."],
        ["2. الحقول الملوّنة بالنيلي إلزامية."],
        ["3. كودات الجهات والمناطق والقطاعات تجدها في ورقة Codes."],
        ["4. تواريخ تكتب بصيغة ISO: YYYY-MM-DD"],
        ["5. القيم المالية أرقام عشرية بدون فواصل."],
        ["6. ورقة Bidders_Detail اختيارية — استخدمها لتسجيل بقية المتنافسين."],
        ["7. لا تحذف الصف الأول (العناوين)."],
        ["8. حفظ بصيغة .xlsx ثم تحميل عبر النظام."],
    ]
    for row in rows:
        instructions.append(row)

    # Sheet 4: Codes (reference codes)
    codes_sheet = wb.create_sheet("Codes")
    codes_sheet.append(["النوع", "الكود", "الاسم"])
    for cell in codes_sheet[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    codes_sheet.append(["region", "RY", "منطقة الرياض"])
    codes_sheet.append(["region", "EP", "المنطقة الشرقية"])
    codes_sheet.append(["region", "MK", "منطقة مكة المكرمة"])
    codes_sheet.append(["sector", "FURN-OFFICE", "أثاث مكتبي"])
    codes_sheet.append(["sector", "CIVIL-BLDG", "مباني"])
    codes_sheet.append(["entity", "NG", "الحرس الوطني"])
    codes_sheet.append(["entity", "MOD", "وزارة الدفاع"])

    return wb


def main(argv=None) -> int:
    argv = list(argv or sys.argv[1:])
    if argv:
        target = Path(argv[0])
    else:
        target = Path(__file__).resolve().parent.parent / "seed_data" / "excel_import_template.xlsx"

    target.parent.mkdir(parents=True, exist_ok=True)
    wb = build_template()
    wb.save(target)
    print(f"Template written to: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
