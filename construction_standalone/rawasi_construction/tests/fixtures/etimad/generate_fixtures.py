#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generates the mandatory Etimad BOQ test fixtures described in SPEC.md Appendix A.

These files are synthetic but faithful to the documented structure of the two
real Etimad template variants:

  - etimad_boq_sample_variant_a.xlsx : 10 columns, quantity in col E (5th),
        description in col F, category column empty, all rows have
        construction_code = "غير محدد", attachments = "لا يوجد مرفقات",
        mandatory_local = "نعم". 39 items.

  - etimad_boq_sample_variant_b.xlsx : 9 columns, quantity in col I (last),
        description in col E, NO attachments column, real SBC codes,
        Forward-Fill category anchors at documented rows, varied unit
        spellings. 209 items.

  - etimad_invalid_not_boq.xlsx : an unrelated (invoice-like) sheet whose
        headers do NOT match the dictionary, used to exercise the
        "reject / fall back to flexible import" path.

Run:  python3 generate_fixtures.py
"""
import os
from openpyxl import Workbook

HERE = os.path.dirname(os.path.abspath(__file__))

# Unit spelling variants that MUST normalize correctly.
# Includes all four linear-meter spellings and both square-meter spellings.
UNIT_VARIANTS = [
    "م²", "م2", "م3", "متر مكعب",
    "م.ط", "م ط", "م/ط", "م . ط",
    "عدد", "مجموعة", "نظام", "كجم", "متر مربع",
]

# Effective category -> SBC construction code (TEXT). "غير محدد" exercises null path.
CATEGORY_SBC = {
    "الأعمال الأولية والموقع العام": "غير محدد",
    "الخرسانة": "2002",
    "الخرسانة مسبقة الصب": "2003",
    "المعادن": "2011",
    "مواد الحماية من الحرارة والرطوبة": "غير محدد",
    "أعمال البناء والطوب": "2007",
    "مواد التشطيب": "2035",
    "السباكة والتركيبات الصحية": "2063",
    "التدفئة والتهوية والتكييف": "2083",
    "شبكات المواسير ومكافحة الحرائق": "2094",
    "الأعمال الكهربائية": "2153",
    "الأبواب والمداخل": "2026",
    "الفتحات والنوافذ": "2031",
    "أعمال التشجير والموقع العام": "2183",
}

# Excel-row -> category text written (anchor). Other rows stay blank (Forward Fill).
# Honors the documented recurrences in Appendix A.3:
#   الخرسانة at rows 9, 38, 42, 196
#   مواد الحماية من الحرارة والرطوبة at rows 39, 43, 46, 124
#   المعادن at rows 30, 36
# Row 1 is the header, so data row for serial N is Excel row N+1.
B_CATEGORY_ANCHORS = {
    2:   "الأعمال الأولية والموقع العام",
    9:   "الخرسانة",
    21:  "الخرسانة مسبقة الصب",
    30:  "المعادن",
    36:  "المعادن",
    38:  "الخرسانة",
    39:  "مواد الحماية من الحرارة والرطوبة",
    42:  "الخرسانة",
    43:  "مواد الحماية من الحرارة والرطوبة",
    46:  "مواد الحماية من الحرارة والرطوبة",
    50:  "أعمال البناء والطوب",
    60:  "مواد التشطيب",
    75:  "السباكة والتركيبات الصحية",
    90:  "التدفئة والتهوية والتكييف",
    105: "شبكات المواسير ومكافحة الحرائق",
    124: "مواد الحماية من الحرارة والرطوبة",
    135: "الأعمال الكهربائية",
    160: "الأبواب والمداخل",
    175: "الفتحات والنوافذ",
    196: "الخرسانة",
    200: "أعمال التشجير والموقع العام",
}

LONG_DESCRIPTION = (
    "توريد وتركيب واختبار وتشغيل كامل لجميع الأعمال المطلوبة شاملةً المواد "
    "والعمالة والمعدات والنقل والمناولة والهالك والتخزين المؤقت في الموقع، "
    "وتنفيذ العمل وفقاً للمخططات التنفيذية المعتمدة من الاستشاري وكود البناء "
    "السعودي (SBC) والمواصفات الفنية العامة لوزارة الدفاع ومتطلبات الجهة "
    "المالكة، بما في ذلك جميع الأعمال التحضيرية والمساندة وأعمال الحماية "
    "والعزل والتشطيب النهائي وإزالة المخلفات وتنظيف الموقع بعد الانتهاء، "
    "مع تقديم جميع شهادات المنشأ وشهادات الجودة ونتائج الاختبارات المعملية "
    "والميدانية اللازمة لاعتماد البند، وضمان مطابقة جميع المواد الموردة "
    "للمواصفات القياسية السعودية ومتطلبات هيئة المحتوى المحلي والمشتريات "
    "الحكومية، على أن يشمل السعر أيضاً أعمال الصيانة خلال فترة الضمان "
    "وإصلاح أي عيوب تظهر خلال تلك الفترة دون أي تكلفة إضافية على الجهة "
    "المالكة، وكذلك التنسيق الكامل مع باقي المقاولين والتخصصات الأخرى في "
    "الموقع لضمان عدم التعارض بين الأعمال وتحقيق التسلسل الزمني المعتمد في "
    "البرنامج الزمني للمشروع، مع الالتزام التام بجميع اشتراطات السلامة "
    "والصحة المهنية المعمول بها في المنشآت الأمنية والعسكرية، وتوفير كافة "
    "وسائل الحماية الشخصية والجماعية للعاملين طوال فترة التنفيذ حتى التسليم "
    "الابتدائي والنهائي للمشروع واعتماده رسمياً من قبل لجنة الاستلام."
)


def build_variant_a(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "BOQ"
    ws.sheet_view.rightToLeft = True

    # 10 columns, quantity at E (index 5), description at F (index 6)
    headers = [
        "الرقم التسلسلي", "الفئة", "البند", "وحدة القياس", "الكمية",
        "وصف البند", "المواصفات", "منتج من القائمة الإلزامية",
        "الرمز الإنشائي", "مرفقات",
    ]
    ws.append(headers)

    groups = ["أعمال مدنية", "أعمال كهربائية", "أعمال ميكانيكية",
              "تشطيبات", "أعمال صحية"]

    for serial in range(1, 40):  # 39 items
        unit = UNIT_VARIANTS[(serial - 1) % len(UNIT_VARIANTS)]
        group = groups[(serial - 1) % len(groups)]
        qty = round(serial * 2.5 + 7.25, 2)
        desc = f"توريد وتركيب {group} رقم {serial} لمبنى المكاتب الأمنية حسب المخططات المعتمدة"
        specs = "" if serial % 5 == 0 else "مطابقة لكود البناء السعودي ومواصفات اعتماد"
        ws.append([
            serial,            # A serial
            None,              # B category (empty for all in Variant A)
            group,             # C group
            unit,              # D unit
            qty,               # E quantity
            desc,              # F description
            specs,             # G specifications
            "نعم",             # H mandatory_local (all yes)
            "غير محدد",        # I construction_code
            "لا يوجد مرفقات",  # J attachments
        ])

    wb.save(path)
    return 39


def build_variant_b(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "BOQ"
    ws.sheet_view.rightToLeft = True

    # 9 columns, description at E (index 5), quantity at I (index 9, last). No attachments.
    headers = [
        "الرقم التسلسلي", "الفئة", "البند", "وحدة القياس", "وصف البند",
        "المواصفات", "منتج من القائمة الإلزامية", "الرمز الإنشائي", "الكمية",
    ]
    ws.append(headers)

    n_items = 209
    for serial in range(1, n_items + 1):  # 209 items
        excel_row = serial + 1

        # Category: write only at anchor rows; blank otherwise (Forward Fill).
        category_cell = B_CATEGORY_ANCHORS.get(excel_row, None)

        # Effective category (for deriving SBC + group + description text).
        effective_cat = None
        for r in range(excel_row, 1, -1):
            if r in B_CATEGORY_ANCHORS:
                effective_cat = B_CATEGORY_ANCHORS[r]
                break
        if effective_cat is None:
            effective_cat = "الأعمال الأولية والموقع العام"

        sbc = CATEGORY_SBC.get(effective_cat, "غير محدد")
        unit = UNIT_VARIANTS[(serial - 1) % len(UNIT_VARIANTS)]
        group = f"{effective_cat} - مجموعة {((serial - 1) % 4) + 1}"

        if serial == 100:
            desc = LONG_DESCRIPTION  # edge case: 1100+ char description
        else:
            desc = f"توريد وتركيب وتنفيذ {effective_cat} - بند رقم {serial} وفق المواصفات الفنية والمخططات المعتمدة"

        specs = "" if serial % 6 == 0 else "حسب كود البناء السعودي والمواصفات القياسية"

        if serial % 7 == 0:
            mandatory = ""        # blank -> NULL (with warning)
        elif serial % 3 == 0:
            mandatory = "لا"
        else:
            mandatory = "نعم"

        qty = round(serial * 1.75 + 3.5, 2)

        ws.append([
            serial,         # A serial
            category_cell,  # B category (anchor only)
            group,          # C group
            unit,           # D unit
            desc,           # E description
            specs,          # F specifications
            mandatory,      # G mandatory_local (mixed)
            sbc,            # H construction_code
            qty,            # I quantity (LAST column)
        ])

    wb.save(path)
    return n_items


def build_invalid(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Invoice"
    ws.sheet_view.rightToLeft = True
    ws.append(["رقم الفاتورة", "التاريخ", "اسم العميل", "المبلغ الإجمالي"])
    ws.append(["INV-001", "2026-01-15", "شركة المثال", 15000])
    ws.append(["INV-002", "2026-01-20", "مؤسسة التجربة", 8400])
    wb.save(path)


if __name__ == "__main__":
    a = build_variant_a(os.path.join(HERE, "etimad_boq_sample_variant_a.xlsx"))
    b = build_variant_b(os.path.join(HERE, "etimad_boq_sample_variant_b.xlsx"))
    build_invalid(os.path.join(HERE, "etimad_invalid_not_boq.xlsx"))
    print(f"Variant A: {a} items (10 cols)")
    print(f"Variant B: {b} items (9 cols)")
    print("Invalid not-BOQ file created.")
