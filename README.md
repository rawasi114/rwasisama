# رواسي سما — موديول إدارة الإنشاءات والمقاولات (Odoo 19)

موديول **أودو 19 (Enterprise)** أصلي يؤتمت الدورة المستندية الكاملة لشركات
المقاولات: من الفرصة (Opportunity) إلى الإغلاق (Closeout).

> **المبدأ المعماري المحوري:** بند جدول الكميات هو النواة الذرية للنظام
> (*BOQ Item is the Atomic Unit*) — كل حركة (طلب مواد، أمر شراء، استلام،
> اعتماد مادة، إنجاز، مستخلص، أمر تغيير) ترتبط ببند BOQ.

## بنية المستودع

```
addons/
  rawasi_construction/        ← موديول أودو
    __manifest__.py
    security/                 ← الفئة + الأدوار السبعة (res.groups.privilege)
    views/                    ← قائمة التطبيق + client action للوحة التحكم
    static/src/dashboard/     ← مكوّن OWL للوحة التحكم
    tests/                    ← اختبارات أودو + ملفات اعتماد (fixtures)
PLAN.md                       ← خطة الفهم والمراحل
PHASE_0_REPORT.md             ← تقرير المرحلة صفر
```

## التثبيت على قاعدة بيانات التطوير

1. انسخ مجلد الموديول إلى مسار الـ addons لديك (أو أضِف هذا المجلد `addons/`
   إلى `addons_path` في ملف إعداد أودو):
   ```
   addons_path = /path/to/odoo/addons, /path/to/rwasisama/addons
   ```
2. أعد تشغيل خادم أودو.
3. من أودو: **التطبيقات (Apps)** ← **تحديث قائمة التطبيقات** ← ابحث عن
   «رواسي سما» ← **تثبيت**.

أو عبر سطر الأوامر:
```bash
odoo-bin -d <db> --addons-path=<odoo>/addons,<repo>/addons -i rawasi_construction
```

## ما يوفّره أودو أصلاً (لا نعيد بناءه)

| المتطلب | حل أودو الأصلي |
|---|---|
| المصادقة وتسجيل الدخول | نظام أودو (`res.users`) |
| الصلاحيات RBAC | `res.groups` + `res.groups.privilege` + record rules |
| الملفات والمرفقات | `ir.attachment` |
| سجل التدقيق (Audit) | `mail.thread` / chatter |
| دعم RTL العربي | تلقائي عند تفعيل اللغة العربية |

## الأدوار السبعة (Personas)

المدير العام · مدير المشاريع · مدير المكتب الفني · مهندس التخطيط ·
مهندس الموقع · المحاسب · الاستشاري الخارجي.

تظهر كحقل اختيار «الدور الوظيفي» في نموذج المستخدم. المدير العام superset
يرث بقية الأدوار.

## التطوير والاختبار

```bash
# تشغيل اختبارات الموديول فقط
odoo-bin -d <db> --addons-path=...,addons --test-tags /rawasi_construction --stop-after-init
```
