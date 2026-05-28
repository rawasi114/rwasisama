# PHASE 0 REPORT — Rawasi Item Catalog

**Branch:** `claude/item-catalog`
**Tag:** `19.0.1.0.0-phase0`
**Status:** ✅ Phase 0 complete — awaiting CEO approval to start Phase 1
**Date:** 2026-05-28

---

## 1. النطاق المُنجَز (Phase 0 Scope Delivered)

| البند | الحالة | الموقع |
|---|---|---|
| إنشاء فرع التطوير | ✅ | `claude/item-catalog` (fork from `main`) |
| هيكل الموديول | ✅ | `addons/rawasi_item_catalog/` |
| `__manifest__.py` (Odoo 19) | ✅ | depends: `base`, `mail`, `uom` — no data files yet |
| `__init__.py` files | ✅ | root, `models/`, `services/`, `tests/` (all placeholder) |
| `migrations/19.0.1.0.0/pre-init.py` | ✅ | `CREATE EXTENSION IF NOT EXISTS vector` |
| الأيقونة (placeholder) | ✅ | `static/description/icon.png` — 256×256 PNG، ألوان رواسي (#253747 / #BD9B5E) |
| `README.md` | ✅ | تعريف الحالة + المراحل القادمة |
| `CHANGELOG.md` | ✅ | إدخال 1.0.0 لـ Phase 0 |

**لم يُكتب أي ملف من ملفات النماذج، الواجهات، الأمان، البذر، أو الاختبارات** — كلها مؤجَّلة بشكل صريح إلى Phase 1+ خلف بوّابة اعتمادك.

---

## 2. فحص البيئة (Environment Discovery)

### 2.1 الإصدارات المؤكَّدة
| المكوّن | الإصدار | الملاحظة |
|---|---|---|
| Odoo | **19** | من manifest الموديولات القائمة (`19.0.8.5.1` لـ rawasi_construction) |
| Python | 3.11 | افتراضي Odoo.sh لـ Odoo 19 |
| PostgreSQL | 16 | افتراضي Odoo.sh |
| pgvector extension | ⚠️ **غير مُتحقَّق منه بعد** | راجع §3 |

### 2.2 فحص التضارب
| فحص | النتيجة |
|---|---|
| `rawasi_pricing_intelligence/` كموديول حالي | ❌ غير موجود — أُعيدت تسميته تاريخياً إلى `rawasi_construction` |
| ملف `master_item.py` | ❌ غير موجود في أي مكان بالريبو |
| موديل `rawasi.item.master` | ❌ غير موجود (آمن للإنشاء) |
| موديل `rawasi.item.taxonomy` | ❌ غير موجود (آمن) |
| موديل `rawasi.item.synonym` | ❌ غير موجود (آمن) |
| تعارض مع `rawasi.boq.item` القائم | ⚪ لا يوجد — كيانان مختلفان مفهومياً (بنود لكل منافسة ≠ كتالوج كنسي) |

**خلاصة:** صفر تعارضات. الموديول يبدأ على أرض نظيفة.

---

## 3. ⚠️ التحقق من pgvector (Pending — يحتاج تنفيذ منك)

**ملاحظة جوهرية:** هذه البيئة (Claude Code) لا تملك وصول shell لـ Odoo.sh، لذا لا أقدر أشغّل `psql` يدوياً للتحقق من حالة الـ extension على dev/staging/production مسبقاً.

**استراتيجية التحقق الموصى بها (تتوافق مع طلبك dev → staging → production):**

### الخيار A — التحقق التلقائي عبر التثبيت (الأبسط، الموصى به)
1. ادمج `claude/item-catalog` → فرع dev/تطوير على Odoo.sh
2. ثبّت الموديول من قائمة Apps في قاعدة الـ dev
3. سيناريوهات النتيجة:
   - ✅ **التثبيت ينجح بدون خطأ** → pgvector مُفعَّل ومتاح. ننتقل لـ Phase 1.
   - ❌ **التثبيت يفشل بخطأ Postgres يقول `permission denied to create extension` أو `extension "vector" is not available`** → نحتاج التفعيل اليدوي عبر دعم Odoo.sh أو من webshell بصلاحية superuser.

### الخيار B — التحقق اليدوي (إذا تبي تفصلهما)
لو تبي تتحقق قبل التثبيت، افتح Odoo.sh → فرع dev → webshell ونفّذ:
```bash
psql -d $PGDATABASE -c "SELECT * FROM pg_available_extensions WHERE name='vector';"
```
- إن طلع صف بـ `installed_version` غير NULL → الـ extension مُفعَّل، تابع التثبيت.
- إن `default_version` غير NULL لكن `installed_version` NULL → الـ extension متاح ولم يُفعَّل بعد، التثبيت سيفعّله.
- إن لا يوجد صف → الـ extension غير متاح على الـ instance — نحتاج طلب تفعيله من دعم Odoo.sh.

**القرار الموصى به:** الخيار A — أرخص وأسرع، والـ `pre-init.py` صُمِّم ليفشل بصمت واضح إن لم تكن الصلاحيات كافية.

---

## 4. الاختلافات عن الـ SPEC (Adaptations)

| الـ SPEC يقول | الواقع المُكيَّف | السبب |
|---|---|---|
| Odoo 17 / 18 | Odoo 19 | بيئتنا فعلياً 19 |
| `feature/master-item-catalog` branch | `claude/item-catalog` | يتبع تقليد `claude/*` للريبو |
| Fork from `main` or `develop` | Fork from `main` فقط | لا يوجد `develop` |
| `.env.staging` ملف منفصل | لا يُستخدم | Odoo.sh يدير الأسرار من لوحة Settings |
| `rawasi_pricing_intelligence` parent | لا parent | الموديول مستقل (إجابتك على السؤال 3) |
| إصدار الموديول `17.0.1.0.0` | `19.0.1.0.0` | يتبع manifest version للـ Odoo |
| المرحلة Phase 2 تحوي wizards | مؤجَّلة (Phase 2 = views فقط) | حسب SPEC §7.2 |

---

## 5. القرارات الفنية في Phase 0

| القرار | الاختيار | المبرر |
|---|---|---|
| `application` flag في manifest | `True` | الموديول كيان مستقل بـ icon ودخول للقائمة الرئيسية مستقبلاً |
| `auto_install` | `False` | يثبَّت يدوياً، لا تبعية تلقائية لموديول آخر |
| `license` | `LGPL-3` | تماشياً مع `rawasi_construction` |
| Embedding dim | 1024 (مؤجَّل لـ Phase 1) | حسب SPEC §5.3 — متوافق مع BGE-M3 |
| Icon style | navy block + gold stripes + white dots | يعكس فكرة الكتالوج الهرمي بألوان رواسي |
| الـ `data:` في manifest | فارغة بالكامل | لا توجد ملفات XML/CSV تُحمَّل في Phase 0 |

---

## 6. التحقق من السلامة (Sanity Checks)

| فحص | النتيجة |
|---|---|
| `python3 -c "import ast; ast.parse(open('addons/rawasi_item_catalog/__manifest__.py').read())"` | ✅ |
| `python3 -c "import ast; ast.parse(open('addons/rawasi_item_catalog/migrations/19.0.1.0.0/pre-init.py').read())"` | ✅ |
| ملف الأيقونة PNG 256×256 صالح | ✅ |
| لا توجد ملفات `.pyc` أو `__pycache__/` مُلتقطة | ✅ — `.gitignore` يحجبها |
| لا توجد لمسة لقاعدة الإنتاج | ✅ — الفرع `claude/item-catalog` لم يُدمج لأي مكان |
| لا توجد لمسة لـ `rawasi_construction` أو `rwasi_workshop` | ✅ — `.gitignore` يحجبها على هذا الفرع |
| لا توجد secrets في الكوميتات | ✅ — لا توجد قيم حساسة كُتبت أصلاً |

---

## 7. مسار النشر المُقتَرَح (Deployment Path)

طلبت dev → staging → production مع التحقق من pgvector في كل خطوة. الخطة:

```
[1] إنا الآن: claude/item-catalog على Odoo.sh dev (بعد ما تعتمد Phase 0)
       ↓ إذا التثبيت نجح والـ pgvector مُفعَّل
[2] دمج إلى Test (staging)
       ↓ إذا التثبيت نجح هناك أيضاً
[3] دمج إلى rawasisama (production)
```

**هذا يحدث فقط بعد كل من Phase 1/2/3 خلف بوّاباتها — Phase 0 وحدها (هيكل فارغ) قد لا تستحق نشراً للستيج/البرودكشن إلا إن أردت التحقق المبكر من pgvector.**

---

## 8. الخيارات المتاحة لك الآن

أ. **اعتماد Phase 0 + بدء Phase 1 فوراً** (الموصى به)
   - أكتب النماذج الخمسة، الأمان، البذر، post-init للـ embedding
   - أقدّم `PHASE_1_REPORT.md` وأتوقف عند البوّابة
   - مدّة تقديرية: ~8.5 ساعات تركيز

ب. **اعتماد Phase 0 + اختبار التثبيت على dev أولاً**
   - تدمج `claude/item-catalog` → فرع dev الفعلي على Odoo.sh
   - تختبر التثبيت → ترجع لي بنتيجة pgvector
   - بعدها أبدأ Phase 1

ج. **تعديل قبل الاعتماد**
   - أشِر للقسم/البند المطلوب تعديله وأنا أُصلِح بدون تقدّم لـ Phase 1

---

## 9. الأسئلة الخمسة من PLAN.md — تذكير بالإجابات المعتمدة

| # | السؤال | إجابتك |
|---|---|---|
| 1 | التحقق من pgvector | **أنا أتحقق بنفسي + dev → staging → production** ← متَّبَع، انظر §3 |
| 2 | اسم الفرع | **داخل النظام، يبدأ على dev** ← `claude/item-catalog` ثم → Test → rawasisama |
| 3 | الأيقونة | **(أ) placeholder بألوان رواسي** ← مُولَّدة، انظر `static/description/icon.png` |
| 4 | تغطية الاختبارات | **أنا أقرر** ← اخترت **pytest --cov محلياً** والتقرير في PHASE_3_REPORT (أبسط، بلا حاجة لـ CI جديد) |
| 5 | أولوية البرودكشن | **مستقر — ابدأ** ← يجري التنفيذ |

---

🛑 **بانتظار اعتمادك على هذا التقرير قبل بدء Phase 1.**

للموافقة، رد بـ: **"وافقت — ابدأ Phase 1"**.
