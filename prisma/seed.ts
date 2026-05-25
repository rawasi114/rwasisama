/**
 * Idempotent seed: permissions, the 7 persona roles, and an admin (CEO) user.
 * Safe to run multiple times (uses upserts).
 */
import { PrismaClient } from '@prisma/client';
import * as bcrypt from 'bcryptjs';

const prisma = new PrismaClient();

const ACTIONS = ['create', 'read', 'update', 'delete', 'manage'] as const;

// Subjects that exist in Phase 0. Later phases extend this list.
const SUBJECTS = ['User', 'Role', 'File', 'AuditLog', 'Dashboard'] as const;

type RoleSeed = {
  key: string;
  nameAr: string;
  nameEn: string;
  // CASL-style grants. { action, subject } | 'manage all'
  grants: Array<{ action: string; subject: string }>;
};

const ALL: { action: string; subject: string } = { action: 'manage', subject: 'all' };
const read = (subject: string) => ({ action: 'read', subject });
const manage = (subject: string) => ({ action: 'manage', subject });

const ROLES: RoleSeed[] = [
  {
    key: 'CEO',
    nameAr: 'المدير العام',
    nameEn: 'Chief Executive Officer',
    grants: [ALL],
  },
  {
    key: 'PROJECTS_DIRECTOR',
    nameAr: 'مدير المشاريع',
    nameEn: 'Projects Director',
    grants: [read('Dashboard'), read('User'), read('AuditLog'), manage('File')],
  },
  {
    key: 'TECH_OFFICE_MANAGER',
    nameAr: 'مدير المكتب الفني',
    nameEn: 'Technical Office Manager',
    grants: [read('Dashboard'), read('User'), manage('File')],
  },
  {
    key: 'PLANNING_ENGINEER',
    nameAr: 'مهندس التخطيط',
    nameEn: 'Planning Engineer',
    grants: [read('Dashboard'), manage('File')],
  },
  {
    key: 'SITE_ENGINEER',
    nameAr: 'مهندس الموقع',
    nameEn: 'Site Engineer',
    grants: [read('Dashboard'), { action: 'create', subject: 'File' }, read('File')],
  },
  {
    key: 'ACCOUNTANT',
    nameAr: 'المحاسب',
    nameEn: 'Accountant',
    grants: [read('Dashboard'), read('File')],
  },
  {
    key: 'EXTERNAL_CONSULTANT',
    nameAr: 'الاستشاري الخارجي',
    nameEn: 'External Consultant',
    grants: [read('Dashboard'), read('File')],
  },
];

async function seedPermissions() {
  const wanted: Array<{ action: string; subject: string }> = [
    { action: 'manage', subject: 'all' },
  ];
  for (const subject of SUBJECTS) {
    for (const action of ACTIONS) {
      wanted.push({ action, subject });
    }
  }
  for (const p of wanted) {
    await prisma.permission.upsert({
      where: { action_subject: { action: p.action, subject: p.subject } },
      update: {},
      create: { action: p.action, subject: p.subject },
    });
  }
  return prisma.permission.findMany();
}

async function main() {
  console.log('Seeding permissions...');
  const permissions = await seedPermissions();
  const permByKey = new Map(permissions.map((p) => [`${p.action}:${p.subject}`, p.id]));

  console.log('Seeding roles...');
  for (const r of ROLES) {
    const role = await prisma.role.upsert({
      where: { key: r.key },
      update: { nameAr: r.nameAr, nameEn: r.nameEn, isSystem: true },
      create: { key: r.key, nameAr: r.nameAr, nameEn: r.nameEn, isSystem: true },
    });
    // Reset and re-apply grants idempotently.
    await prisma.rolePermission.deleteMany({ where: { roleId: role.id } });
    for (const g of r.grants) {
      const permId = permByKey.get(`${g.action}:${g.subject}`);
      if (!permId) continue;
      await prisma.rolePermission.create({
        data: { roleId: role.id, permissionId: permId },
      });
    }
  }

  console.log('Seeding admin user...');
  const ceo = await prisma.role.findUniqueOrThrow({ where: { key: 'CEO' } });
  const email = process.env.SEED_ADMIN_EMAIL ?? 'admin@rawasi-sama.sa';
  const password = process.env.SEED_ADMIN_PASSWORD ?? 'Admin@12345';
  const cost = Number(process.env.BCRYPT_COST ?? 12);
  const passwordHash = await bcrypt.hash(password, cost);

  await prisma.user.upsert({
    where: { email },
    update: { roleId: ceo.id, isActive: true },
    create: {
      email,
      passwordHash,
      fullNameAr: 'مدير النظام',
      fullNameEn: 'System Administrator',
      roleId: ceo.id,
      isActive: true,
    },
  });

  console.log(`Done. Admin: ${email}`);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
