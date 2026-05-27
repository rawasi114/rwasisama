# Rawasi Pricing Intelligence System

نظام التسعير الذكي لمنافسات شركة رواسي سما للمقاولات.

## نظرة عامة

منصة استخبارات تنافسية تحوّل البيانات التاريخية وبيانات منصة اعتماد إلى:
- معرفة سعر السوق المرجعي لأي بند خلال ثوانٍ
- تقدير حجم وقيمة المنافسات الجديدة
- تحليل سلوك المنافسين تاريخياً
- اتخاذ قرار Go/No-Go سريع مبني على بيانات
- معرفة احتمالية الفوز عند نقطة سعر معينة

## البنية المعمارية

النظام مبني على 5 طبقات:

1. **Layer 1 — Data Ingestion:** ثلاث قنوات إدخال (يدوي، مدعوم Claude، جماعي Excel)
2. **Layer 2 — Normalization:** قاموس بنود + تطابق دلالي
3. **Layer 3 — Data Storage:** PostgreSQL + pgvector
4. **Layer 4 — Analytics Engines:** أربعة محركات تحليلية متوازية
5. **Layer 5 — User Interface:** Odoo Module + Dashboards

## الحزمة التقنية

- Python 3.11+
- FastAPI
- PostgreSQL 16 + pgvector
- SQLAlchemy 2.x + Alembic
- Anthropic Claude API (Sonnet)
- pandas, scikit-learn, scipy
- Docker + docker-compose

## التشغيل السريع

```bash
cp .env.example .env
docker-compose up -d db
pip install -e ".[dev]"
alembic upgrade head
python scripts/seed_reference_data.py
uvicorn api.main:app --reload
pytest
```

## بيئات النشر

- **dev:** فرع `claude/intelligent-carson-SAFBz` — التطوير اليومي
- **staging:** فرع `staging` — اختبار قبل البرودكشن
- **production:** فرع `main` — البرودكشن

## المراجع

- [المواصفات الكاملة](docs/SPECIFICATION.md)
- [دليل المطور](docs/DEVELOPER_GUIDE.md)
- [دليل النشر](docs/DEPLOYMENT.md)
- [دليل API](docs/API.md)
