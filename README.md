# رواسي سما — نظام ERP الموحَّد (Odoo 19)

نظام تخطيط موارد لـ **شركة رواسي سما للمقاولات** على Odoo 19.0 / Python 3.12+،
عربيّ RTL بالكامل، وفق الأمر الهندسي الموحَّد **RAW-ERP-2026-002**.

> سجل تجاري ٢٥١١١٢٦٥٢٧ · رقم ضريبي ٣١١٠٧٠١٣١٩٠٠٠٠٣ · https://www.rawasisama.com

## المعمارية (ثلاثة موديولات)

```
rawasi_base (الأساس المشترك)
   ├── الهوية البصرية (Navy #253747 · Gold #BD9B5E · Cairo)
   ├── المجموعات المشتركة (أدمن · محاسب · مشتريات)
   ├── شجرة الحسابات (٢٧٢ حساب) + الخطط التحليلية متعددة الأبعاد
   └── الأصول الثابتة (rawasi.equipment)
        ▲                                   ▲
rawasi_construction                  rawasi_workshop
   (منافسات · BoQ · مشاريع ·            (أقسام · أوامر تصنيع ·
    DSR · IPC · VO)                      بوابات دفع · تصنيع داخلي)
            └──── التصنيع الداخلي (Cross-Module) ────┘
```

## الموديولات

| الموديول | الوصف | يعتمد على |
|---|---|---|
| [`rawasi_base`](./rawasi_base) | الأساس المشترك | `account`, `stock`, `purchase`, `sale`, `hr`, … |
| [`rawasi_construction`](./rawasi_construction) | إدارة المقاولات | `rawasi_base`, `project`, `stock_account` |
| [`rawasi_workshop`](./rawasi_workshop) | إدارة الورشة | `rawasi_base`, `sale`, `stock_account` |

## التثبيت

```bash
# النظام كاملاً على قاعدة بيانات نظيفة
odoo -d rawasi -i rawasi_base,rawasi_construction,rawasi_workshop

# موديول فرعي بمفرده (يُثبَّت rawasi_base تلقائياً عبر depends)
odoo -d rawasi -i rawasi_construction
```

## خطة التنفيذ المرحلية

| المرحلة | المحتوى | الحالة |
|---|---|---|
| **Phase 0** | البنية الأساسية للموديولات الثلاثة (manifests, __init__, security, menus) | ✅ |
| **Phase 1** | الهوية البصرية + المجموعات + شجرة الحسابات + الخطط التحليلية + الأصول | ✅ |
| **Phase 2** | الإشعارات + DMS + Audit + سلاسل الاعتماد + PIN + الإعدادات | ⏳ |
| **Phase 3** | قاعدة طلب المواد المجرّدة + اختبارات الأساس | ⏳ |
| **Phase 4** | المقاولات: المنافسة + المشروع + BoQ + الكتالوج + BoM | ⏳ |
| **Phase 5** | المقاولات: المخزون + MR + PO + DSR + IPC + VO + الضمانات | ⏳ |
| **Phase 6** | الورشة: الأقسام + MO + تكامل البيع + بوابات الدفع + التقارير | ⏳ |
| **Phase 7** | التكامل: التصنيع الداخلي + النقل التلقائي + التحليل المزدوج | ⏳ |
| **Phase 8** | الاختبارات الشاملة + التوثيق + السيناريوهات الكاملة | ⏳ |

## التطوير

```bash
# التحقق من صحة البنية (Python + XML + CSV + المانيفست) دون تشغيل Odoo
python3 tools/validate_modules.py

# تنزيل خط Cairo الحر (عند توفّر الشبكة)
bash tools/fetch_fonts.sh
```

---
© شركة رواسي سما للمقاولات — رخصة LGPL-3
