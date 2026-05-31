# دليل التطوير والتحقق — رواسي سما ERP

## نظرة عامة
أربعة موديولات Odoo 19 (عربي RTL):
`rawasi_base` → `rawasi_construction` + `rawasi_workshop` → `rawasi_integration`.

## التحقق السريع (بلا Odoo)
أداة فحص offline تتحقق من سلامة المانيفست، وجود الملفات المرجعية، صحة Python،
سلامة XML، واتساق ملفات الصلاحيات CSV:

```bash
python3 tools/validate_modules.py
```

## التحقق الكامل (Odoo 19 فعلي)
تمّ التحقق من النظام على **Odoo 19.0 + PostgreSQL 16** فعلياً (تثبيت نظيف + كامل
حزمة الاختبارات). خطوات إعادة الإنتاج:

### 1) PostgreSQL
```bash
# عبر مدير عناقيد ديبيان (يسقط لمستخدم postgres تلقائياً)
pg_ctlcluster 16 main start
su postgres -c "psql -c \"CREATE ROLE odoo SUPERUSER LOGIN PASSWORD 'odoo';\""
su postgres -c "createdb -O odoo rawasi_test"
```

### 2) Odoo 19 + التبعيات (venv معزول)
```bash
git clone --depth 1 --branch 19.0 --single-branch https://github.com/odoo/odoo.git /tmp/odoo
python3 -m venv /tmp/ov
/tmp/ov/bin/pip install babel psycopg2-binary werkzeug lxml lxml_html_clean pillow \
  reportlab python-dateutil pytz passlib decorator docutils jinja2 markupsafe \
  num2words psutil python-stdnum qrcode requests polib rjsmin freezegun pyopenssl \
  idna urllib3 cryptography greenlet gevent vobject zeep xlrd xlsxwriter openpyxl \
  chardet asn1crypto cbor2 pyusb
# ملاحظة: python-ldap اختياري (LDAP فقط) وقد يفشل بناؤه بلا libldap-dev — يُستثنى.
```

### 3) تثبيت نظيف لكل الموديولات
```bash
HOME=/tmp /tmp/ov/bin/python /tmp/odoo/odoo-bin \
  -d rawasi_test --db_host=localhost --db_port=5432 --db_user=odoo --db_password=odoo \
  --addons-path=/tmp/odoo/addons,$PWD \
  -i rawasi_base,rawasi_construction,rawasi_workshop,rawasi_integration \
  --stop-after-init --without-demo=all --log-level=warn
```
**النتيجة المتحققة:** `Modules loaded. Registry loaded.` — **0 ERROR / 0 WARNING / 0 CRITICAL**.

### 4) تشغيل الاختبارات
```bash
HOME=/tmp /tmp/ov/bin/python /tmp/odoo/odoo-bin \
  -d rawasi_test --db_host=localhost --db_port=5432 --db_user=odoo --db_password=odoo \
  --addons-path=/tmp/odoo/addons,$PWD \
  -u rawasi_base,rawasi_construction,rawasi_workshop,rawasi_integration \
  --test-enable --stop-after-init --log-level=test
```

## حالة الاختبارات (متحققة)

| الموديول | عدد الاختبارات | الحالة |
|---|---|---|
| `rawasi_base` | 17 | ✅ |
| `rawasi_construction` | 21 | ✅ |
| `rawasi_workshop` | 9 | ✅ |
| `rawasi_integration` | 14 | ✅ |
| **الإجمالي** | **61** | ✅ 0 فشل / 0 أخطاء |

## سيناريوهات القبول (PART F) — مغطّاة باختبارات
- **S1 — مقاولات نقي:** منافسة → BoQ → فوز → مشروع → MR → صرف → DSR → IPC → دفع → ضمان.
- **S2 — ورشة نقي:** MO + بوابات دفع (٥٠٪/١٠٠٪) → تصنيع → تسليم (`rawasi_workshop`).
- **S3 — التصنيع الداخلي:** بند `in_house_workshop` → MR → أمر تصنيع داخلي → SO داخلي →
  MO بلا بوابة دفع → نقل تلقائي للمشروع → قفل MR.
- **S4 — تجاوز إداري:** يُسجَّل في `rawasi.audit.trail` المشترك (append-only).
- **S5 — دور عابر:** محاسب واحد يعتمد ميزانية المقاولات + ميزانية الورشة بـ session واحد.
- **S6 — تحليل متعدد الأبعاد:** خطتان منفصلتان (مشاريع المقاولات / أقسام الورشة) تحت جذر «رواسي».

## ملاحظات بيئية
- الأصول البصرية (خط Cairo) عبر تدرّج خطوط آمن؛ للإنتاج استخدم `tools/fetch_fonts.sh`.
- شجرة الحسابات (٢٧٢) مُولّدة من المصدر المعتمد، مع تصحيح نوع الحساب 71031 إلى `expense`.
- قوائم الأصول (PDF) صور ممسوحة؛ تُستورد عبر قالب `rawasi_base/data/equipment_import_template.csv`.
