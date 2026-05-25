# رواسي سما — موديول إدارة الإنشاءات والمقاولات (Rawasi Sama ERP)

نظام ERP لإدارة دورة حياة مشاريع المقاولات الحكومية لشركة رواسي سما للمقاولات، من
الفرصة (Opportunity) في منصة اعتماد حتى الإغلاق والمستخلص النهائي، مع ذاكرة تسعير ذكية.

> **المبدأ المعماري الحاكم:** *بند جدول الكميات هو الكيان المحوري (BOQ Item is the Atomic Unit).*
> كل حركة في النظام ترتبط ببند BOQ.

المرجع الكامل للمتطلبات في [`SPEC.md`](./SPEC.md)، وخطة التنفيذ في [`PLAN.md`](./PLAN.md).

---

## المكدّس التقني (Tech Stack)

| الطبقة | التقنية |
|---|---|
| Monorepo | pnpm workspaces + Turborepo |
| Frontend (`apps/web`) | Next.js 14 (App Router) · TypeScript · TailwindCSS · next-intl (RTL) · TanStack Query · Zustand |
| Backend (`apps/api`) | NestJS 10 · Prisma 5 · Passport JWT · CASL (RBAC) · Pino · Swagger |
| Database | PostgreSQL 16 |
| Cache / Jobs | Redis 7 (BullMQ — مراحل لاحقة) |
| Storage | قرص محلي (تطوير) · S3/MinIO (إنتاج — مرحلة لاحقة) |

## هيكل المشروع

```
apps/
  api/   # NestJS API  (auth, RBAC, files, audit, lookups)
  web/   # Next.js     (RTL shell, login, dashboard)
.github/workflows/ci.yml
docker-compose.yml
```

---

## التشغيل محلياً (Getting Started)

### المتطلبات
- Node.js 20+، pnpm 10+
- PostgreSQL 16 و Redis 7 (عبر Docker أو محلياً)

### الخطوات

```bash
# 1) تثبيت الحزم
pnpm install

# 2) تشغيل قاعدة البيانات والخدمات
docker compose up -d postgres redis

# 3) إعداد متغيرات البيئة
cp .env.example apps/api/.env   # عدّل القيم عند الحاجة

# 4) قاعدة البيانات: التهجير والبيانات الأولية
pnpm --filter @rawasi/api db:deploy   # تطبيق الـ migrations
pnpm --filter @rawasi/api db:seed     # الوحدات + رموز SBC + الأدوار + admin

# 5) التشغيل (API على 4000، الواجهة على 3000)
pnpm dev
```

- الواجهة: <http://localhost:3000>
- توثيق الـ API (Swagger): <http://localhost:4000/api/docs>
- فحص الصحة: <http://localhost:4000/api/health>

### حساب الدخول الأولي (بعد الـ seed)
- البريد: `admin@rawasi-sama.sa`
- كلمة المرور: `Admin@12345` (الدور: CEO)

> ⚠️ غيّر بيانات الدخول والأسرار (JWT secrets) قبل أي نشر إنتاجي.

---

## أوامر مفيدة (Scripts)

| الأمر | الوظيفة |
|---|---|
| `pnpm dev` | تشغيل API + Web معاً |
| `pnpm build` | بناء كل التطبيقات |
| `pnpm lint` | فحص الأنواع (tsc) |
| `pnpm test` | الاختبارات |
| `pnpm --filter @rawasi/api db:migrate` | إنشاء/تطبيق migration جديد |
| `pnpm --filter @rawasi/api db:seed` | إعادة زرع البيانات الأولية |

---

## حالة التطوير

المرحلة الحالية: **المرحلة صفر (التأسيس)** — مكتملة. التفاصيل في
[`PHASE_0_REPORT.md`](./PHASE_0_REPORT.md). المراحل التالية في القسم ٨ من `SPEC.md`.
