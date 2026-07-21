# النشر والبنية — نشرتان متنافيتان (Two Mutually-Exclusive Deployments)

> **تنبيه معماري:** هذا المستودع يحوي **منتجَين منفصلين تماماً** (صفر إشارات
> متبادلة بينهما). لا يتعايشان في نفس قاعدة بيانات Odoo لأنهما يعرّفان نفس
> الموديلات (`rawasi.competition`, `rawasi.boq.item`, `rawasi.material.request`…)
> بمخططات مختلفة. **اختر نشرة واحدة فقط لكل قاعدة بيانات.**

تاريخياً نشأ المنتجان من فرعين بفلسفتين مختلفتين (انظر [`README.md`](./README.md)
لِـ Stack A و [`PLAN.md`](./PLAN.md) لِـ Stack B) ثم دُمجا في مستودع واحد. تعارض
الاسم التقني الوحيد (`rawasi_construction` مكرَّر) حُلَّ بفصلهما فيزيائياً في
جذرَي `addons_path` مختلفين، **دون حذف أي كود**؛ قرار «أيّ منتج نعتمده أو ندمجهما»
مؤجَّل عن قصد.

---

## النشرة أ — النظام الموحّد (Stack A · جذر المستودع)

```
rawasi_base  →  rawasi_construction  +  rawasi_workshop  →  rawasi_integration
```

| البند | القيمة |
|---|---|
| `addons_path` | جذر المستودع (`/path/to/rwasisama`) |
| التثبيت | `odoo --addons-path=/path/to/rwasisama -d db_unified -i rawasi_integration` |
| المقاولات | **v1 (مبكّرة)** — يستخدم `rawasi.dsr` / `rawasi.bom` |
| المزايا | أساس مشترك (هوية بصرية، ٢٧٢ حساباً، خطط تحليلية، إشعارات، DMS، تدقيق، اعتماد PIN) + مقاولات (BoQ/DSR/IPC/VO/ضمانات) + **ورشة** + **التصنيع الداخلي + لوحة موحّدة** |

> تثبيت `rawasi_integration` يجرّ تلقائياً `rawasi_base` و`rawasi_construction`
> و`rawasi_workshop` عبر سلسلة التبعيات.

---

## النشرة ب — المقاولات المستقلة (Stack B · `construction_standalone/`)

```
rawasi_construction  +  rawasi_competitions  +  rawasi_construction_gantt
```

| البند | القيمة |
|---|---|
| `addons_path` | `/path/to/rwasisama/construction_standalone` |
| التثبيت | `odoo --addons-path=/path/to/rwasisama/construction_standalone -d db_construction -i rawasi_construction,rawasi_competitions,rawasi_construction_gantt` |
| المقاولات | **v11 (ناضجة)** — يستخدم `rawasi.daily.report` / `rawasi.goods.receipt` |
| المزايا | استيراد BoQ ذكي عربي · ذكاء تسعيري · مقاولو باطن + مستخلصاتهم · MAS · NCR/RFI · GRN · شهادات دفع · Gantt · لوحة. **لا ورشة ولا تكامل ولا أساس مشترك.** |

---

## ⚠️ قاعدة حاسمة

**لا تضع جذر المستودع و`construction_standalone/` في نفس `addons_path` أبداً.**
كلاهما يحوي موديولاً اسمه التقني `rawasi_construction`؛ سيُحمّل Odoo الأول فقط حسب
ترتيب المسار ويتجاهل الآخر صمتاً، والموديلات المشتركة ستتعارض في السجلّ (registry).

---

## ملاحظة: موديول يتيم (Orphan)

`rwasi_workshop/` (في الجذر، بادئة `rwasi.*`، ~٢٢٩١ سطراً، **بلا اختبارات**) لا
يعتمد عليه أيّ موديول ولا يشير لغيره. هو **ورشة بديلة** عن `rawasi_workshop`
(بادئة `rawasi.workshop.*`، المستخدَمة فعلياً في Stack A). مُبقى دون حذف بانتظار
قرار: **دمجه** مع `rawasi_workshop` أو **إزالته**.

---

## التحقق (Validation)

```bash
python3 tools/validate_modules.py
```

يفحص الأداة الآن **كل** الموديولات في الجذر و`construction_standalone/`، ويتحقق من:
المانيفست، وجود الملفات المشار إليها، صحّة Python/XML، اتساق `ir.model.access.csv`،
**وتكرار الأسماء التقنية داخل الجذر الواحد** (خطأ). كما تُصدر **إشعاراً** (notice)
عن الموديولات المكرّرة عبر النشرتين — وهو تكرار مقصود يؤكّد وجوب عدم تحميلهما معاً.
