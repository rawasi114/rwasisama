# رواسي سما — نظام ERP الموحَّد (Odoo 19)

نظام تخطيط موارد لـ **شركة رواسي سما للمقاولات** على Odoo 19.0 / Python 3.12+،
عربيّ RTL بالكامل، وفق الأمر الهندسي الموحَّد **RAW-ERP-2026-002**.

> سجل تجاري ٢٥١١١٢٦٥٢٧ · رقم ضريبي ٣١١٠٧٠١٣١٩٠٠٠٠٣ · https://www.rawasisama.com

> ⚠️ **يحوي هذا المستودع نشرتين متنافيتين** لا تتعايشان في نفس قاعدة البيانات.
> ما يلي يصف **النشرة أ (النظام الموحّد · جذر المستودع)**. توجد أيضاً **النشرة ب
> (مقاولات مستقلة ناضجة) في `construction_standalone/`**. اقرأ [`DEPLOYMENT.md`](./DEPLOYMENT.md)
> قبل التثبيت لاختيار النشرة الصحيحة وضبط `addons_path`.

## المعمارية (أربعة موديولات)

```
rawasi_base (الأساس المشترك)
   ├── الهوية البصرية (Navy #253747 · Gold #BD9B5E · Cairo)
   ├── المجموعات المشتركة (أدمن · محاسب · مشتريات)
   ├── شجرة الحسابات (٢٧٢ حساب) + الخطط التحليلية متعددة الأبعاد
   ├── الأصول الثابتة (rawasi.equipment)
   ├── الإشعارات (notification.hook) + DMS + سجل التدقيق
   ├── سلاسل الاعتماد + PIN + الإعدادات الموحدة
   └── قاعدة طلب المواد المجرّدة (material.request.base)
        ▲                                   ▲
rawasi_construction                  rawasi_workshop
   • منافسات + BoQ + كتالوج            • أقسام (نجارة/حدادة)
   • مشاريع + BoM                      • أوامر تصنيع + بوابات دفع
   • MR + DSR + VO + IPC + ضمانات       • تكامل البيع + صرف بـ PIN
        └────────────┬──────────────────────┘
              rawasi_integration
        • التصنيع الداخلي (السيناريو الذهبي)
        • النقل التلقائي + التحليل المزدوج + اللوحة الموحدة
```

## الموديولات

| الموديول | الوصف | يعتمد على |
|---|---|---|
| [`rawasi_base`](./rawasi_base) | الأساس المشترك | `account`, `stock`, `purchase`, `sale`, `hr`, … |
| [`rawasi_construction`](./rawasi_construction) | إدارة المقاولات | `rawasi_base`, `project`, `stock_account` |
| [`rawasi_workshop`](./rawasi_workshop) | إدارة الورشة | `rawasi_base`, `sale_management`, `stock_account` |
| [`rawasi_integration`](./rawasi_integration) | التصنيع الداخلي + اللوحة الموحدة | `rawasi_construction`, `rawasi_workshop` |

## التثبيت

```bash
# النظام كاملاً على قاعدة بيانات نظيفة
odoo -d rawasi -i rawasi_base,rawasi_construction,rawasi_workshop,rawasi_integration

# موديول فرعي بمفرده (تُثبَّت تبعياته تلقائياً)
odoo -d rawasi -i rawasi_integration
```

## خطة التنفيذ المرحلية

| المرحلة | المحتوى | الحالة |
|---|---|---|
| **Phase 0** | البنية الأساسية للموديولات (manifests, security, menus) | ✅ |
| **Phase 1** | الهوية + المجموعات + شجرة الحسابات + الخطط التحليلية + الأصول | ✅ |
| **Phase 2** | الإشعارات + DMS + Audit + سلاسل الاعتماد + PIN + الإعدادات | ✅ |
| **Phase 3** | قاعدة طلب المواد المجرّدة + معالج PIN + اختبارات الأساس | ✅ |
| **Phase 4** | المقاولات: الكتالوج + المنافسة + BoQ + المشروع + BoM | ✅ |
| **Phase 5** | المقاولات: MR + DSR + VO + IPC + الضمانات | ✅ |
| **Phase 6** | الورشة: الأقسام + MO + بوابات الدفع + تكامل البيع | ✅ |
| **Phase 7** | التكامل: التصنيع الداخلي + النقل التلقائي + اللوحة الموحدة | ✅ |
| **Phase 8** | الاختبارات الشاملة + التوثيق + السيناريوهات الكاملة | ✅ |

## الاختبارات والتحقق

```bash
# التحقق من صحة البنية (Python + XML + CSV + المانيفست) دون تشغيل Odoo
python3 tools/validate_modules.py

# تشغيل اختبارات Odoo (مع خادم Odoo 19 + PostgreSQL)
odoo -d rawasi_test -i rawasi_base,rawasi_construction,rawasi_workshop,rawasi_integration \
     --test-enable --stop-after-init
```

تمّ التحقق من النظام بتثبيت **Odoo 19 فعلي** على قاعدة بيانات نظيفة + تشغيل
حزمة الاختبارات (TransactionCase) — انظر [`DEVELOPMENT.md`](./DEVELOPMENT.md).

## التطوير

```bash
# تنزيل خط Cairo الحر (عند توفّر الشبكة)
bash tools/fetch_fonts.sh
```

---
© شركة رواسي سما للمقاولات — رخصة LGPL-3
