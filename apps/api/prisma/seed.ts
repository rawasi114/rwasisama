/**
 * Rawasi Sama ERP — Database seed (Phase 0).
 * Idempotent: safe to run repeatedly. Seeds RBAC (roles + permissions),
 * the units lookup (with real alias spellings observed in the Etimad
 * fixtures), the SBC code lookup, and the initial admin user.
 */
import { PrismaClient, UnitCategory } from '@prisma/client';
import * as bcrypt from 'bcryptjs';

const prisma = new PrismaClient();

// ---------------------------------------------------------------------------
// RBAC: resources × actions
// ---------------------------------------------------------------------------
const RESOURCES = [
  'opportunity', 'project', 'boq', 'wbs', 'material_request', 'purchase_order',
  'goods_receipt', 'document', 'mas', 'dsr', 'ncr', 'rfi', 'variation_order',
  'payment_certificate', 'bank_guarantee', 'pricing_intelligence', 'subcontractor',
  'dashboard', 'user', 'role', 'audit_log', 'file', 'unit', 'sbc_code',
] as const;

const ACTIONS = ['create', 'read', 'update', 'delete', 'approve', 'export'] as const;

type Perm = { resource: string; action: string };
const ALL: Perm[] = RESOURCES.flatMap((r) => ACTIONS.map((a) => ({ resource: r, action: a })));

const grant = (resources: string[], actions: string[]): Perm[] =>
  resources.flatMap((r) => actions.map((a) => ({ resource: r, action: a })));

const readAll: Perm[] = RESOURCES.map((r) => ({ resource: r, action: 'read' }));

// الأدوار السبعة من الدستور
const ROLES: { name: string; nameAr: string; description: string; perms: Perm[] | 'ALL' }[] = [
  { name: 'CEO', nameAr: 'المدير العام', description: 'رؤية كاملة واعتماد التجاوزات', perms: 'ALL' },
  {
    name: 'PROJECTS_DIRECTOR', nameAr: 'مدير المشاريع',
    description: 'إدارة محفظة المشاريع وتخصيص الفرق واعتماد المراحل',
    perms: [
      ...readAll,
      ...grant(['project', 'wbs', 'variation_order', 'payment_certificate', 'bank_guarantee'], ['create', 'update', 'approve']),
      ...grant(['material_request'], ['approve']),
      ...grant(['dashboard'], ['export']),
    ],
  },
  {
    name: 'TECH_OFFICE_MANAGER', nameAr: 'مدير المكتب الفني',
    description: 'إعداد العروض والتسعير وإدارة المستندات الفنية',
    perms: [
      ...grant(['opportunity', 'boq', 'document', 'mas'], ['create', 'read', 'update', 'approve', 'export']),
      ...grant(['project', 'pricing_intelligence', 'dashboard'], ['read']),
      ...grant(['dashboard'], ['export']),
    ],
  },
  {
    name: 'PLANNING_ENGINEER', nameAr: 'مهندس التخطيط',
    description: 'بناء الجداول الزمنية وWBS وتحديث نسب الإنجاز',
    perms: [
      ...grant(['wbs'], ['create', 'read', 'update', 'delete', 'export']),
      ...grant(['boq', 'project', 'document', 'dashboard', 'dsr'], ['read']),
    ],
  },
  {
    name: 'SITE_ENGINEER', nameAr: 'مهندس الموقع',
    description: 'طلبات المواد وتقارير DSR وNCR (بدون رؤية التكاليف)',
    perms: [
      ...grant(['material_request', 'dsr', 'ncr'], ['create', 'read', 'update']),
      ...grant(['goods_receipt', 'rfi'], ['create', 'read']),
      ...grant(['document', 'project', 'boq'], ['read']),
    ],
  },
  {
    name: 'ACCOUNTANT', nameAr: 'المحاسب',
    description: 'المستخلصات والفواتير والضمانات والتقارير المالية',
    perms: [
      ...grant(['payment_certificate', 'bank_guarantee'], ['create', 'read', 'update', 'export']),
      ...grant(['purchase_order', 'goods_receipt', 'project', 'document'], ['read']),
      ...grant(['dashboard'], ['read', 'export']),
    ],
  },
  {
    name: 'EXTERNAL_CONSULTANT', nameAr: 'الاستشاري الخارجي',
    description: 'عرض المستندات المخصصة والرد على اعتمادات المواد والاستفسارات',
    perms: [
      ...grant(['mas', 'rfi'], ['read', 'update']),
      ...grant(['document', 'project'], ['read']),
    ],
  },
];

// ---------------------------------------------------------------------------
// Units lookup — aliases مأخوذة حرفياً من الدستور (تشمل الكتابات المُلاحظة في الملفين)
// ---------------------------------------------------------------------------
const UNITS: {
  canonicalCode: string; canonicalNameAr: string; canonicalNameEn: string;
  displaySymbolAr: string; category: UnitCategory; aliases: string[];
}[] = [
  { canonicalCode: 'SQM', canonicalNameAr: 'متر مربع', canonicalNameEn: 'Square Meter', displaySymbolAr: 'م²', category: 'AREA', aliases: ['متر مربع', 'م2', 'م 2', 'م^2', 'م²', 'م.مربع', 'م مربع', 'sqm', 'sq.m', 'm2', 'm²'] },
  { canonicalCode: 'CBM', canonicalNameAr: 'متر مكعب', canonicalNameEn: 'Cubic Meter', displaySymbolAr: 'م³', category: 'VOLUME', aliases: ['متر مكعب', 'م3', 'م 3', 'م^3', 'م³', 'م.مكعب', 'م مكعب', 'cbm', 'm3', 'm³'] },
  { canonicalCode: 'LM', canonicalNameAr: 'متر طولي', canonicalNameEn: 'Linear Meter', displaySymbolAr: 'م.ط', category: 'LENGTH', aliases: ['متر طولي', 'م ط', 'م/ط', 'م.ط', 'م . ط', 'م-ط', 'م ط.', 'م.ط.', 'linear meter', 'lm', 'rm', 'rmt'] },
  { canonicalCode: 'M', canonicalNameAr: 'متر', canonicalNameEn: 'Meter', displaySymbolAr: 'م', category: 'LENGTH', aliases: ['متر', 'م', 'meter', 'm'] },
  { canonicalCode: 'EA', canonicalNameAr: 'عدد', canonicalNameEn: 'Each', displaySymbolAr: 'عدد', category: 'COUNT', aliases: ['عدد', 'رقم', 'قطعة', 'وحدة', 'piece', 'pcs', 'each', 'ea', 'no', 'nr'] },
  { canonicalCode: 'SET', canonicalNameAr: 'مجموعة', canonicalNameEn: 'Set', displaySymbolAr: 'مجموعة', category: 'GROUP', aliases: ['مجموعة', 'طقم', 'set', 'kit', 'lot'] },
  { canonicalCode: 'SYS', canonicalNameAr: 'نظام', canonicalNameEn: 'System', displaySymbolAr: 'نظام', category: 'SYSTEM', aliases: ['نظام', 'system', 'sys', 'package'] },
  { canonicalCode: 'KG', canonicalNameAr: 'كيلوجرام', canonicalNameEn: 'Kilogram', displaySymbolAr: 'كجم', category: 'WEIGHT', aliases: ['كيلوجرام', 'كيلوغرام', 'كجم', 'كغ', 'كلغ', 'kg', 'kilo'] },
  { canonicalCode: 'TON', canonicalNameAr: 'طن', canonicalNameEn: 'Ton', displaySymbolAr: 'طن', category: 'WEIGHT', aliases: ['طن', 'ton', 'tonne', 't'] },
  { canonicalCode: 'LITER', canonicalNameAr: 'لتر', canonicalNameEn: 'Liter', displaySymbolAr: 'لتر', category: 'VOLUME', aliases: ['لتر', 'ل', 'liter', 'litre', 'l'] },
  { canonicalCode: 'LS', canonicalNameAr: 'مقطوع', canonicalNameEn: 'Lump Sum', displaySymbolAr: 'مقطوع', category: 'OTHER', aliases: ['مقطوع', 'إجمالي', 'جملة', 'lump sum', 'ls'] },
  { canonicalCode: 'HOUR', canonicalNameAr: 'ساعة', canonicalNameEn: 'Hour', displaySymbolAr: 'ساعة', category: 'OTHER', aliases: ['ساعة', 'ساعات', 'hour', 'hr', 'hrs'] },
  { canonicalCode: 'DAY', canonicalNameAr: 'يوم', canonicalNameEn: 'Day', displaySymbolAr: 'يوم', category: 'OTHER', aliases: ['يوم', 'أيام', 'day', 'd'] },
];

// ---------------------------------------------------------------------------
// SBC codes — أسماء الأقسام حسب النطاقات المُلاحظة في الملحق أ.٦
// ---------------------------------------------------------------------------
function sbcNameForCode(code: number): string {
  const exact: Record<number, string> = {
    2002: 'الخرسانة المصبوبة في الموقع',
    2003: 'الخرسانة مسبقة الصب',
    2007: 'أعمال البناء (الطوب والبلوك)',
    2009: 'الواجهات والكسوات الخارجية',
    2011: 'الأعمال المعدنية',
    2026: 'الأبواب والمداخل',
    2031: 'الفتحات والنوافذ',
    2183: 'أعمال التشجير والموقع العام',
  };
  if (exact[code]) return exact[code];
  if (code >= 2035 && code <= 2058) return 'مواد التشطيب';
  if (code >= 2063 && code <= 2067) return 'السباكة والتركيبات الصحية';
  if (code >= 2073 && code <= 2079) return 'أبنية وبنى جاهزة';
  if (code >= 2083 && code <= 2092) return 'مواد التدفئة والتهوية والتكييف';
  if (code >= 2094 && code <= 2106) return 'شبكات المواسير ومكافحة الحرائق';
  if (code >= 2124 && code <= 2127) return 'الخدمات والمرافق';
  if (code >= 2153 && code <= 2172) return 'الأعمال الكهربائية';
  return `قسم SBC ${code}`;
}

const SBC_CODES = [
  2002, 2003, 2007, 2009, 2011, 2026, 2031, 2035, 2036, 2037, 2039, 2040, 2041,
  2046, 2048, 2049, 2054, 2055, 2057, 2058, 2063, 2064, 2065, 2066, 2067, 2073,
  2074, 2078, 2079, 2083, 2086, 2087, 2088, 2091, 2092, 2094, 2096, 2100, 2103,
  2104, 2106, 2124, 2125, 2127, 2153, 2158, 2159, 2165, 2172, 2183,
];

async function main() {
  console.log('🌱 Seeding Rawasi Sama ERP database...');

  // 1) Permissions
  await prisma.permission.createMany({ data: ALL, skipDuplicates: true });
  const permRows = await prisma.permission.findMany();
  const permId = new Map(permRows.map((p) => [`${p.resource}:${p.action}`, p.id]));
  console.log(`  ✅ permissions: ${permRows.length}`);

  // 2) Roles
  for (const role of ROLES) {
    const perms = role.perms === 'ALL' ? ALL : role.perms;
    const connect = perms
      .map((p) => permId.get(`${p.resource}:${p.action}`))
      .filter((id): id is string => Boolean(id))
      .map((id) => ({ id }));
    await prisma.role.upsert({
      where: { name: role.name },
      update: { nameAr: role.nameAr, description: role.description, isSystem: true, permissions: { set: connect } },
      create: { name: role.name, nameAr: role.nameAr, description: role.description, isSystem: true, permissions: { connect } },
    });
  }
  console.log(`  ✅ roles: ${ROLES.length}`);

  // 3) Units
  for (const u of UNITS) {
    await prisma.unitLookup.upsert({
      where: { canonicalCode: u.canonicalCode },
      update: { ...u },
      create: { ...u },
    });
  }
  console.log(`  ✅ units_lookup: ${UNITS.length}`);

  // 4) SBC codes
  for (const code of SBC_CODES) {
    await prisma.sbcCode.upsert({
      where: { code },
      update: { codeGroup: Math.floor(code / 100), nameAr: sbcNameForCode(code) },
      create: { code, codeGroup: Math.floor(code / 100), nameAr: sbcNameForCode(code) },
    });
  }
  console.log(`  ✅ sbc_codes_lookup: ${SBC_CODES.length}`);

  // 5) Admin user (CEO)
  const ceo = await prisma.role.findUniqueOrThrow({ where: { name: 'CEO' } });
  const email = process.env.SEED_ADMIN_EMAIL ?? 'admin@rawasi-sama.sa';
  const password = process.env.SEED_ADMIN_PASSWORD ?? 'Admin@12345';
  const rounds = Number(process.env.BCRYPT_SALT_ROUNDS ?? 12);
  const passwordHash = await bcrypt.hash(password, rounds);
  await prisma.user.upsert({
    where: { email },
    update: { roleId: ceo.id, isActive: true },
    create: { email, passwordHash, fullNameAr: 'مدير النظام', fullNameEn: 'System Administrator', roleId: ceo.id },
  });
  console.log(`  ✅ admin user: ${email}`);

  console.log('🌱 Seed complete.');
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
