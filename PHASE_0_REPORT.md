# تقرير المرحلة صفر — التأسيس (Phase 0: Foundation)

> **الحالة:** ✅ مكتملة ومُتحقّق منها end-to-end على قاعدة بيانات PostgreSQL حقيقية.
> **بانتظار موافقتك قبل الانتقال للمرحلة الأولى.**

---

## ١. ملخص الإنجاز

تم تأسيس البنية الكاملة للمشروع: **Monorepo** يعمل، قاعدة بيانات بأول migration،
نظام **مصادقة JWT** مع تدوير refresh tokens، نظام **صلاحيات RBAC دقيق (CASL)**،
نظام **ملفات** بتجريد تخزين (local/S3)، نظام **تدقيق (Audit)**، توثيق **OpenAPI/Swagger**
تلقائي، وواجهة **Next.js** بـ RTL عربي كامل (صفحة دخول + لوحة فارغة).

**النتيجة العملية (مخرج المرحلة المطلوب):** نظام يمكن تسجيل الدخول إليه بمستخدمين
بأدوار مختلفة، وكل دور يرى ما تسمح به صلاحياته فقط. تم إثبات ذلك فعلياً:
المدير العام (CEO) يقرأ المستخدمين، ومهندس الموقع يُمنع (403).

---

## ٢. ما تم بناؤه

### البنية (Monorepo)
- **pnpm workspaces + Turborepo** مع مهام: `build`, `dev`, `lint`, `typecheck`, `test`.
- `tsconfig.base.json` مشترك، و path aliases: `@rawasi/shared-types`, `@rawasi/utils`.
- `.env.example` موثّق بالكامل، `.gitignore`، إعداد TypeScript صارم (strict).

### قاعدة البيانات (Prisma + PostgreSQL 16)
- `prisma/schema.prisma` بجداول المرحلة صفر: `roles`, `permissions`,
  `role_permissions`, `users`, `refresh_tokens`, `files`, `file_links`
  (polymorphic), `audit_logs`.
- أول migration مطبّق (`migrations/…_init`).
- `prisma/seed.ts` (idempotent): الصلاحيات + الأدوار السبعة + مستخدم admin.

### الواجهة الخلفية (NestJS + REST + OpenAPI)
- **Auth:** `POST /auth/login`, `POST /auth/refresh` (مع **تدوير** الرمز وإبطاله)،
  `POST /auth/logout`, `GET /auth/me`. كلمات المرور بـ **bcrypt (cost 12)**.
- **RBAC (CASL):** `JwtAuthGuard` عام + `PoliciesGuard` + `@CheckPolicies(...)`.
  الصلاحيات تُحمَّل **طازجة من DB** عند كل طلب (تغيير الصلاحية يسري فوراً).
- **Users:** `GET /users`, `GET /users/:id`, `POST /users` (محميّة بسياسات).
- **Files:** رفع/تنزيل/حذف + ربط polymorphic، خلف **StorageService** بسائقين
  (`LocalStorageDriver` للتطوير، `S3StorageDriver` لـ MinIO/S3) + checksum SHA-256.
- **Audit:** `AuditService` يسجّل العمليات الحساسة (لا يكسر التدفق إن فشل).
- **الأمان:** `helmet`, CORS, `ValidationPipe` (whitelist + forbidNonWhitelisted),
  **rate limiting** (Throttler)، فلتر أخطاء موحّد بالعربية.
- **التسجيل:** `nestjs-pino` مع **correlation id** (`x-request-id`) وإخفاء
  الحقول الحساسة (authorization, password).
- **التوثيق:** Swagger على `/api/docs` و `/api/docs-json`.

### الواجهة الأمامية (Next.js 14 App Router)
- **RTL كامل** (`dir="rtl"`, `lang="ar"`) + ألوان الهوية (Navy `#253747`,
  Gold `#BD9B5E`) عبر Tailwind.
- صفحة **تسجيل دخول** (React Hook Form) + **لوحة تحكم فارغة** محمية + تسجيل خروج.
- `auth-store` (Zustand + persist)، عميل `axios` يضيف الـ Bearer token،
  `TanStack Query`، نصوص عربية عبر `next-intl`.

### الحزم المشتركة
- `@rawasi/shared-types`: أنواع DTO وأدوار مشتركة بين الواجهتين.
- `@rawasi/utils`: `normalizeArabicLight`, `normalizeUnit` (أساس الاستيراد الذكي
  والذكاء التسعيري لاحقاً)، `formatSAR`، `VAT_RATE` — مع اختبارات.

### DevOps
- `docker-compose.yml` (postgres, redis, minio, api, web) + **Dockerfiles**
  متعددة المراحل للـ api والـ web.
- **GitHub Actions CI**: install → prisma generate → validate → typecheck → test → build.

---

## ٣. نتائج التحقق (Verification)

| الفحص | النتيجة |
|---|---|
| `pnpm typecheck` | ✅ 5/5 packages |
| `pnpm test` | ✅ **30 اختبار** (23 api + 7 utils) |
| `pnpm build` | ✅ api + web + packages |
| `prisma validate` | ✅ valid |
| migration + seed على PostgreSQL حقيقي | ✅ |

### اختبار end-to-end حيّ (على PostgreSQL 16 محلي)
| السيناريو | المتوقّع | النتيجة |
|---|---|---|
| `GET /api/health` | db up | ✅ `{"status":"ok","db":"up"}` |
| تسجيل دخول admin | tokens + user | ✅ |
| `/auth/me` برمز صالح | 200 | ✅ |
| `/auth/me` بدون رمز | 401 | ✅ |
| كلمة مرور خاطئة | 401 | ✅ |
| تدوير refresh token | رمز جديد + إبطال القديم | ✅ (4 صادرة / 1 مُبطل) |
| CEO يقرأ `/users` | 200 | ✅ |
| **مهندس الموقع يقرأ `/users`** | **403** | ✅ رسالة عربية |
| Swagger `/api/docs` | 200 | ✅ |
| تسجيل LOGIN في `audit_logs` | يُسجَّل | ✅ (3 إدخالات) |

---

## ٤. كيفية التشغيل

### عبر Docker (الموصى به للإنتاج/التكامل)
```bash
cp .env.example .env
docker compose up -d            # postgres + redis + minio + api + web
pnpm prisma:migrate             # أو migrate deploy في الإنتاج
pnpm prisma:seed
# web:  http://localhost:3000   |  api docs: http://localhost:4000/api/docs
```

### محلياً للتطوير
```bash
pnpm install && pnpm prisma:generate
# شغّل PostgreSQL ثم:
pnpm prisma:migrate && pnpm prisma:seed
pnpm dev                        # يشغّل api + web عبر turbo
```

**حساب الدخول الأولي:** `admin@rawasi-sama.sa` / `Admin@12345` (دور CEO).

---

## ٥. انحرافات مبرَّرة عن المواصفات (شفافية)

1. **i18n:** استُخدم `next-intl` بنمط locale واحد (ar) بدون توجيه locale-prefixed
   لتقليل المخاطر في التأسيس؛ يمكن ترقيته للتوجيه الكامل عند الحاجة لاحقاً.
2. **الخط:** الهوية تتطلب **DIN Next LT Arabic** (سؤال مفتوح #4). مؤقتاً نستخدم
   خطوط النظام (Tahoma)؛ سنضمّن الخط الرسمي عند توفّر ملفاته (مهم لتضمين PDF في م٤).
3. **ESLint:** مؤجّل للواجهة الخلفية في هذه المرحلة (الأمان النوعي مضمون عبر
   `tsc` الصارم)؛ الواجهة الأمامية تستخدم `eslint-config-next`.
4. **bcryptjs** بدل `bcrypt` الأصلي (نقي JS) لتفادي مشاكل البناء الأصلي في CI/Docker.

---

## ٦. قيود بيئة التطوير الحالية

- **Docker daemon غير مُشغَّل** في بيئة التنفيذ الحالية، لذا لم أتمكّن من تشغيل
  `docker compose` هنا. **بديلاً عن ذلك**، شغّلت **PostgreSQL 16 محلياً** وأجريت
  التحقق end-to-end الكامل (جدول القسم ٣). ملفات Docker مكتوبة وجاهزة للتشغيل في
  أي بيئة بها daemon.

---

## ٧. معايير قبول المرحلة صفر

- ✅ نظام يمكن تسجيل الدخول إليه بمستخدمين بأدوار مختلفة.
- ✅ لوحة فارغة + RTL setup.
- ✅ Auth + RBAC + Files + Audit + Logging تعمل وتم التحقق منها.
- ✅ أول migration + seed.
- ✅ CI + Docker جاهزة.

---

## ٨. الخطوة التالية

بانتظار موافقتك للانتقال إلى **المرحلة الأولى** (إدارة المنافسات + الاستيراد الذكي
لقالب اعتماد + التسعير + التحويل لمشروع). ملفّا الـ fixtures جاهزان لتطوير الاستيراد
الذكي مباشرةً. تبقى أسئلة مفتوحة بسيطة من `PLAN.md` (مكتبة Gantt للمرحلة الثانية،
ملفات الخط للمرحلة الرابعة) لا تعيق بدء المرحلة الأولى.
