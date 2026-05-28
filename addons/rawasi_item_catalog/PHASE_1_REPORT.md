# PHASE 1 REPORT — Rawasi Item Catalog

**Branch:** `claude/item-catalog`
**Module version:** `19.0.1.1.0`
**Status:** ✅ Phase 1 complete — awaiting CEO approval to start Phase 2
**Date:** 2026-05-28

---

## 1. النطاق المُنجَز

### 1.1 النماذج الخمسة
| الموديل | الملف | الميزات الرئيسية |
|---|---|---|
| `rawasi.item.taxonomy` | `models/item_taxonomy.py` | `_parent_store`، 4 مستويات، قيد تسلسل صارم (level_parent = level_child − 1)، حماية من الحلقات، `display_name_full` recursive |
| `rawasi.item.master` | `models/item_master.py` | كود كنسي بـ regex `XXX-XXX-XXXX-NNN`، taxonomy_id مقيد بـ subcategory فقط، tracking لحالة المراجعة، حقول in_house/workshop_type |
| `rawasi.item.synonym` | `models/item_synonym.py` | `_compute_normalized` عربي-aware، unique(canonical, normalized)، تتبع تكرار/تواريخ ظهور/ثقة |
| `rawasi.item.attribute` | `models/item_attribute.py` | 10 مفاتيح مُعرَّفة + custom key، قيد منطقي لاستخدام custom فقط مع «أخرى» |
| `rawasi.item.mapping.audit` | `models/item_mapping_audit.py` | append-only، 4 مصادر اقتراح، 4 أنواع إجراء مستخدم، تتبع الاقتراح الأصلي قبل التعديل |

### 1.2 الأمان (3 مجموعات + 15 قاعدة وصول)
| المجموعة | XML ID | الصلاحيات |
|---|---|---|
| قارئ | `group_item_catalog_user` | قراءة فقط (5 نماذج) |
| محرّر | `group_item_catalog_editor` | قراءة + كتابة + إنشاء (يرث القارئ) |
| مدير | `group_item_catalog_admin` | كل ما سبق + حذف (يرث المحرّر) |

`ir.model.access.csv`: 15 سطر = 5 نماذج × 3 مجموعات.

### 1.3 بذر البيانات
`data/taxonomy_root_seed.xml` يحوي 5 شعب جذرية بـ `noupdate="1"` (محمية من overwrite):
- `ARCH` — الأعمال المعمارية
- `STRC` — الأعمال الإنشائية
- `ELEC` — الأعمال الكهربائية
- `MECH` — الأعمال الميكانيكية
- `INHS` — التصنيع الداخلي

### 1.4 pgvector عبر post_init_hook (بدل migration)
الـ SPEC يضع `post-init.py` في `migrations/`. لكن في Odoo 19، scripts الـ migrations تُشغَّل فقط عند **upgrade** (لا تشتغل على install أول مرة).

**الحل المعتمد:** نقلت العمل إلى `pre_init_hook` و`post_init_hook` في الـ manifest — تشتغل في الحالتين (install + upgrade):

- `_pre_init_hook` → `CREATE EXTENSION IF NOT EXISTS vector`
- `_post_init_hook` → `ALTER TABLE ... ADD COLUMN embedding vector(1024)` + `CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)` لكل من `rawasi_item_master` و`rawasi_item_synonym`

ملف `migrations/19.0.1.0.0/pre-init.py` السابق محتفظ به للحماية (يفيد سيناريو upgrade من نسخة قديمة جداً، لا يضر إن أُعيد).

---

## 2. دالة التطبيع العربي — جودة فحوصها

دالة `normalize_arabic` في `item_synonym.py` تخضع لـ 10 حالات اختبار يدوي قبل الـ commit:

| # | المُدخَل | المُخرَج | تعليق |
|---|---|---|---|
| 1 | `  خَرَسانَةٌ مُسَلَّحَة  ` | `خرسانة مسلحة` | تشكيل + مسافات |
| 2 | `بَلَاطْ بُورْسِلَانْ` | `بلاط بورسلان` | كل أنواع التشكيل |
| 3 | `أنابيب PVC قُطْر 110` | `انابيب pvc قطر 110` | ألف الهمزة + lowercase + تشكيل |
| 4 | `إِطَارٌ آلَة` | `اطار الة` | جميع variants الألف |
| 5 | `قِطْعَة رقم ٢٥` | `قطعة رقم 25` | الأرقام العربية |
| 6 | `قطعة رقم ۲۵` | `قطعة رقم 25` | الأرقام الفارسية |
| 7 | `بـــلاط` | `بلاط` | التطويل |
| 8 | `على` | `علي` | ألف مقصورة → ياء |
| 9 | `''` | `''` | فارغ |
| 10 | `None` | `''` | حماية من None |

**نتيجة:** 10/10 ✓

**قرار متعمَّد:** الـ ة (تاء مربوطة) تبقى ولا تُحوَّل إلى ه. مصطلحات فنية تعتمد على التمييز (مثلاً «ساعة» vs «ساعه»).

---

## 3. القيود (Constraints) المنفَّذة

| الموديل | القيد | المستوى | الرسالة |
|---|---|---|---|
| taxonomy | `UNIQUE(code)` | DB | كود التصنيف يجب أن يكون فريداً |
| taxonomy | hierarchy consistency | Python | مستوى الابن = مستوى الأب + 1 |
| taxonomy | no parent for division | Python | الشعبة لا يمكن أن يكون لها أب |
| taxonomy | no cycle | Python | لا يمكن إنشاء حلقة |
| master | `UNIQUE(canonical_code)` | DB | الكود الكنسي فريد |
| master | code regex | Python | يتبع نمط XXX-XXX-XXXX-NNN |
| master | taxonomy must be subcategory | Python | البنود تُربط بفئات فرعية فقط |
| synonym | `UNIQUE(canonical_item_id, text_normalized)` | DB | لا تكرار صياغة مُطبَّعة |
| attribute | custom key only with «أخرى» | Python | منطق المفتاح المخصص |

---

## 4. السلامة (Sanity Checks)

| فحص | النتيجة |
|---|---|
| Python AST parse على كل 7 ملفات `.py` | ✅ |
| XML parse على `security.xml` + `taxonomy_root_seed.xml` | ✅ |
| CSV: 16 سطر = 1 header + 5 نماذج × 3 مجموعات | ✅ |
| 10/10 حالات normalize_arabic | ✅ |
| لا توجد لمسة لـ `rawasi_construction` أو `rwasi_workshop` | ✅ |
| لا توجد secrets | ✅ |
| Odoo 19 idioms (`models.Constraint`) — لا `_sql_constraints` deprecated | ✅ |

---

## 5. مسار التحقق المقترح

1. **Push** فرع `claude/item-catalog` → Odoo.sh يبني dev تلقائياً (الحالي)
2. **Upgrade** الموديول من Apps في قاعدة الـ dev
3. سيناريوهات النتيجة:

| السيناريو | المعنى | الإجراء |
|---|---|---|
| ✅ Upgrade ينجح + 5 شعب تظهر عند `SELECT * FROM rawasi_item_taxonomy` | كل شيء سليم | المضي لـ Phase 2 |
| ❌ خطأ pgvector `extension does not exist` | pre_init_hook فشل (صلاحيات أو غياب المكتبة) | تواصل دعم Odoo.sh |
| ❌ خطأ `column vector(1024) doesn't fit` | البُعد قد لا يكون مدعوماً (نادر) | نقلّل إلى 768 ونعيد |
| ❌ خطأ Python في تحميل الموديل | حقل أو import | أصلح فوراً |

**ملاحظة عملية:** هذا upgrade وليس install جديد. الـ post_init_hook يشتغل **مرة واحدة على install الأول** ولا يُعيد عند الـ upgrade. بما إنك ثبّتت Phase 0 سابقاً، الـ upgrade الحالي **لن يستدعي post_init_hook**.

لإجبار تشغيل الـ embedding columns، إما:
- (أ) إلغاء تثبيت الموديول ثم إعادة التثبيت (يعيد install كاملاً → post_init_hook يشتغل)
- (ب) أنقل منطق إنشاء الأعمدة إلى `migrations/19.0.1.1.0/post-init.py` (يشتغل على هذا الـ upgrade تحديداً)

**أنصح بـ (ب)** لتفادي حذف أي بيانات بذرتها يدوياً. لو وافقت، أضيف الملف الآن قبل اعتماد Phase 1.

---

## 6. الأرقام

| المقياس | القيمة |
|---|---|
| ملفات Python جديدة | 7 |
| ملفات XML جديدة | 2 |
| ملفات CSV جديدة | 1 |
| إجمالي أسطر الكود | ~520 |
| الموديلات | 5 |
| القيود | 9 |
| مجموعات الأمان | 3 |
| سجلات البذر | 5 |
| حالات اختبار تطبيع | 10/10 |

---

## 7. الخيارات المتاحة لك الآن

أ. **اعتماد Phase 1 + اختبار Upgrade على dev**
   - تروح Odoo.sh → dev → Apps → Upgrade
   - تتأكد من ظهور 5 شعب في الـ DB أو UI (تحت Settings → Technical → Models)
   - ترجعلي بالنتيجة قبل ما أبدأ Phase 2

ب. **اعتماد Phase 1 + إضافة migration للـ embedding أولاً**
   - أضيف `migrations/19.0.1.1.0/post-init.py` ليشتغل في الـ upgrade الحالي
   - تختبر، ثم أبدأ Phase 2

ج. **تعديل قبل الاعتماد** — أشِر للقسم/البند المطلوب تعديله

---

🛑 **بانتظار اعتمادك. أنصح بالخيار (ب) لضمان تشغيل الـ embedding columns على هذا الـ upgrade.**
