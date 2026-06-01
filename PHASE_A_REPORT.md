# تقرير المرحلة A — التصنيفات + إثراء البند المرجعي + حقول جدول الكميات

> الحالة: **مكتملة بانتظار اعتمادك**. لن أبدأ المرحلة B قبل موافقتك.
> الفرع: `claude/wizardly-cerf-HRAUG` · الموديول: `rawasi_construction` · لم يُلمَس الإنتاج.

---

## 1. ما أُنجز

### أ) نموذجا التصنيف
- **`rawasi.lcgpa.code`** (`models/lcgpa_code.py`) — رمز هيئة المحتوى المحلي.
  حقول: `code` (فريد، ≤10)، `name_ar` (إلزامي)، `name_en`، `category`، `description`،
  `is_mandatory_local`، `display_label` (محسوب مخزّن `[code] name_ar`)، علاقة عكسية
  `reference_item_ids` + عدّاد، `active`. دالة `match_code` للمطابقة (تُستخدم لاحقاً بالاستيراد).
- **`rawasi.sbc.code`** (`models/sbc_code.py`) — رمز كود البناء السعودي.
  حقول: `code` (فريد)، `name` (مترجَم)، `display_label` (`code - name`)، `active` + `match_code`.

### ب) إثراء البند المرجعي (`rawasi.reference.item`)
- إضافة `lcgpa_code_id` و`sbc_code_id` (Many2one للنموذجين أعلاه) + إظهارهما في الفورم ضمن مجموعة «التصنيفات».

### ج) حقول جدول الكميات (`rawasi.boq.item`) — الأعمدة العشرة المطلوبة
| العمود المطلوب | الحقل | الحالة |
|---|---|---|
| الرقم التسلسلي | `serial` | **مضاف** |
| الفئة | `category` | **مضاف** |
| الوصف | `description` | موجود |
| المواصفات | `specification` | موجود |
| الكمية | `qty` | موجود |
| وحدة القياس | `uom_id` | موجود |
| التكلفة الإفرادي | `unit_cost` | **مضاف (قابل للتحرير)** |
| إجمالي التكلفة للبند | `total_cost` | **مضاف (محسوب = الكمية×التكلفة)** |
| السعر الإفرادي | `unit_price` | موجود (أُعيدت تسميته) |
| إجمالي البند | `subtotal` | موجود (محسوب = الكمية×السعر) |

- تحديث `_onchange_reference_item`: يملأ `unit_cost` و`unit_price` من التكلفة المعيارية للبند المرجعي إن كانا فارغين.
- تحديث قائمة BOQ في فورم المنافسة لتعرض الأعمدة العشرة بالترتيب.

### د) البيانات البذرية
- `data/rawasi.lcgpa.code.csv` — **65 رمز LCGPA** مُولّدة من `lcgpa_codes_seed.csv`
  (معرّفات خارجية `lcgpa_<code>`، الاسم = التصنيف العام، الوصف = عيّنة بند).

### هـ) الواجهات والقوائم والصلاحيات
- `views/classification_views.xml` — قوائم/فورم/بحث للنموذجين + عنصرا قائمة تحت «الكتالوج».
- `security/ir.model.access.csv` — 11 سطر صلاحيات (تقني/أدمن تحرير، الباقي قراءة).
- ربط `models/__init__.py` و`__manifest__.py` (CSV + الواجهة، بالترتيب الصحيح للقوائم).

---

## 2. الاختبارات
ملف `tests/test_phaseA_classification.py` — **12 اختباراً**: display_label لكلا الرمزين،
بذر CSV، تفرّد الرمز، `match_code` (شامل «غير محدد»/الفارغ)، عدّاد البنود المرجعية،
ربط التصنيفات بالبند المرجعي، حساب `total_cost`/`subtotal`، وافتراضات `_onchange`.
> لا تشغيل محلي (لا Odoo محلياً) — يُبنى ويُختبر على Odoo.sh عند الدفع للفرع التطويري.

التحقق المنفّذ محلياً: تحليل صياغة Python + XML + CSV — **كلها سليمة**.

---

## 3. الملفات المتأثرة
**جديدة:** `models/lcgpa_code.py` · `models/sbc_code.py` · `views/classification_views.xml` ·
`data/rawasi.lcgpa.code.csv` · `tests/test_phaseA_classification.py`
**معدّلة:** `models/reference_item.py` · `models/competition.py` · `models/__init__.py` ·
`__manifest__.py` · `security/ir.model.access.csv` · `views/reference_item_views.xml` ·
`views/competition_views.xml` · `tests/__init__.py`

---

## 4. قرارات اتُّخذت (للمراجعة)
1. **اسم رمز LCGPA البذري** = التصنيف العام (مثل «الخرسانة») والوصف = عيّنة البند، لأن المصدر لا يحوي اسماً قانونياً للرمز. قابل للإثراء لاحقاً.
2. **`category` في BOQ** نص حر (لا يُملأ تلقائياً من تصنيف البند المرجعي تفادياً لتخزين مفتاح إنجليزي).
3. **رموز SBC** بلا بذر (لا يوجد ملف مصدر) — تُدخل يدوياً أو في مرحلة لاحقة.

---

## 5. التالي (بعد اعتمادك)
**المرحلة B — ذاكرة التسعير** (`rawasi.price.intelligence` + مطابقة فجوية + لوحة «أسعار تاريخية مشابهة»).

> سؤال مفتوح من الخطة: الورشة — هل أُبقيها مبسّطة فقط، أم تريد لاحقاً نماذج جودة/صيانة/HSE؟ (الافتراضي: مبسّطة).
