# رواسي سما — كتالوج البنود الموحَّد

**Rawasi Item Catalog** — Master canonical-item registry for the Rawasi Sama contracting ERP.

## الهدف
تحويل النصوص الخام لجداول الكميات (~25,000 صياغة بديلة سنوياً) إلى ~5,000 بند كنسي موحَّد قابل للاستعلام والتحليل.

## الحالة الحالية
**Phase 0** — هيكل الموديول الفارغ فقط:
- `__manifest__.py` (Odoo 19، يعتمد على base/mail/uom)
- `migrations/19.0.1.0.0/pre-init.py` — يفعّل امتداد pgvector
- هياكل مجلدات `models/`، `views/`، `security/`، `data/`، `services/`، `tests/`، `i18n/`
- لا توجد نماذج، لا واجهات، لا منطق أعمال بعد

## المراحل القادمة
| المرحلة | المحتوى | الحالة |
|---|---|---|
| Phase 1 | 5 نماذج + الأمان + بذر الشعب الخمس + post-init للـ embedding columns | ⏸ بانتظار اعتماد Phase 0 |
| Phase 2 | كل الواجهات (Tree / Form / Kanban / Hierarchy / Search) + القائمة | ⏸ |
| Phase 3 | اختبارات (≥80% تغطية) + توثيق + Claude stub | ⏸ |

## التثبيت (Phase 0)
1. تأكَّد أن قاعدة Postgres لديها صلاحية `CREATE EXTENSION` (افتراضي على Odoo.sh)
2. ثبّت الموديول من قائمة التطبيقات في Odoo: «رواسي سما — كتالوج البنود الموحَّد»
3. عند التثبيت: `pre-init.py` يفعّل `vector` extension تلقائياً
4. الموديول يُثبَّت بنجاح بدون ظهور أي شاشة (لا توجد نماذج بعد)

## إلغاء التثبيت
آمن في Phase 0 — لا توجد جداول مُنشأة من الـ ORM. امتداد pgvector يبقى مُفعَّلاً على القاعدة (لا يُحذف بـ uninstall).

## المرجع
- مواصفات كاملة: `/SPEC.md`
- خطة التنفيذ بالمهام الذرية: `/PLAN.md`
- تقرير Phase 0: `/PHASE_0_REPORT.md`
