"""Seed initial reference data: government entities, regions, cities, sectors.

This script is idempotent — it inserts missing rows but does not delete or
update existing ones. Safe to run on every deployment.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.core.database import SessionLocal
from api.core.logging import configure_logging, get_logger
from api.models import City, GovernmentEntity, MasterItem, Region, Sector

LOG = get_logger(__name__)
SEED_DIR = Path(__file__).resolve().parent.parent / "seed_data"


REGIONS = [
    ("RY", "منطقة الرياض", "Riyadh"),
    ("MK", "منطقة مكة المكرمة", "Makkah"),
    ("MD", "منطقة المدينة المنورة", "Madinah"),
    ("QS", "منطقة القصيم", "Qassim"),
    ("EP", "المنطقة الشرقية", "Eastern Province"),
    ("AS", "منطقة عسير", "Aseer"),
    ("TB", "منطقة تبوك", "Tabuk"),
    ("HA", "منطقة حائل", "Hail"),
    ("NB", "منطقة الحدود الشمالية", "Northern Borders"),
    ("JZ", "منطقة جازان", "Jazan"),
    ("NJ", "منطقة نجران", "Najran"),
    ("BH", "منطقة الباحة", "Al-Bahah"),
    ("JF", "منطقة الجوف", "Al-Jouf"),
]


CITIES = [
    ("RYD", "الرياض", "RY"),
    ("JED", "جدة", "MK"),
    ("MEC", "مكة المكرمة", "MK"),
    ("MED", "المدينة المنورة", "MD"),
    ("DAM", "الدمام", "EP"),
    ("KHB", "الخبر", "EP"),
    ("DHA", "الظهران", "EP"),
    ("ABH", "أبها", "AS"),
    ("KMT", "خميس مشيط", "AS"),
    ("TBK", "تبوك", "TB"),
    ("HAI", "حائل", "HA"),
    ("ARR", "عرعر", "NB"),
    ("JAZ", "جازان", "JZ"),
    ("NAJ", "نجران", "NJ"),
    ("BUR", "بريدة", "QS"),
    ("UNZ", "عنيزة", "QS"),
    ("AHS", "الأحساء", "EP"),
    ("JUB", "الجبيل", "EP"),
    ("YNB", "ينبع", "MK"),
    ("TAI", "الطائف", "MK"),
]


SECTORS = [
    ("CIVIL", "أعمال مدنية وإنشائية", "Civil Works", None),
    ("CIVIL-BLDG", "مباني", "Buildings", "CIVIL"),
    ("CIVIL-ROAD", "طرق وجسور", "Roads & Bridges", "CIVIL"),
    ("CIVIL-INFRA", "بنية تحتية", "Infrastructure", "CIVIL"),
    ("FURN", "أثاث", "Furniture", None),
    ("FURN-OFFICE", "أثاث مكتبي", "Office Furniture", "FURN"),
    ("FURN-EDU", "أثاث تعليمي", "Educational Furniture", "FURN"),
    ("FURN-HEALTH", "أثاث طبي", "Medical Furniture", "FURN"),
    ("FINISH", "تشطيبات", "Finishings", None),
    ("FINISH-PAINT", "دهانات", "Paint", "FINISH"),
    ("FINISH-FLOOR", "أرضيات", "Flooring", "FINISH"),
    ("MEP", "أعمال كهروميكانيكية", "MEP Works", None),
    ("MEP-HVAC", "تكييف وتهوية", "HVAC", "MEP"),
    ("MEP-ELEC", "كهرباء", "Electrical", "MEP"),
    ("MEP-PLUMB", "سباكة", "Plumbing", "MEP"),
    ("MAINT", "صيانة وتشغيل", "Maintenance", None),
    ("SUPPLY", "توريد مواد", "Material Supply", None),
    ("CLEAN", "نظافة", "Cleaning Services", None),
    ("SEC", "حراسة وأمن", "Security Services", None),
]


GOVERNMENT_ENTITIES = [
    ("MOD", "وزارة الدفاع", "Ministry of Defense", "military"),
    ("NG", "الحرس الوطني", "National Guard", "military"),
    ("MOI", "وزارة الداخلية", "Ministry of Interior", "security"),
    ("MOH", "وزارة الصحة", "Ministry of Health", "health"),
    ("MOE", "وزارة التعليم", "Ministry of Education", "education"),
    ("MOF", "وزارة المالية", "Ministry of Finance", "civil"),
    ("MOJ", "وزارة العدل", "Ministry of Justice", "civil"),
    ("MOIA", "وزارة الشؤون الإسلامية", "Ministry of Islamic Affairs", "civil"),
    ("MOMRA", "وزارة الشؤون البلدية", "Ministry of Municipal Affairs", "civil"),
    ("MOL", "وزارة العمل", "Ministry of Labor", "civil"),
    ("MEWA", "وزارة البيئة والمياه والزراعة", "Ministry of Environment", "civil"),
    ("MOC", "وزارة التجارة", "Ministry of Commerce", "civil"),
    ("MOT", "وزارة النقل", "Ministry of Transport", "civil"),
    ("MOFA", "وزارة الخارجية", "Ministry of Foreign Affairs", "civil"),
    ("KAUST", "جامعة الملك عبدالله", "KAUST", "education"),
    ("KSU", "جامعة الملك سعود", "King Saud University", "education"),
    ("KAU", "جامعة الملك عبدالعزيز", "KAU", "education"),
    ("ARAMCO", "أرامكو", "Saudi Aramco", "civil"),
    ("SABIC", "سابك", "SABIC", "civil"),
    ("SCE", "الهيئة السعودية للمهندسين", "SCE", "civil"),
]


INITIAL_MASTER_ITEMS = [
    ("CONC-RC-25", "خرسانة مسلحة بمقاومة 25 ميجا باسكال للأساسات", "m3", "civil"),
    ("CONC-RC-30", "خرسانة مسلحة بمقاومة 30 ميجا باسكال للأساسات", "m3", "civil"),
    ("CONC-RC-35", "خرسانة مسلحة بمقاومة 35 ميجا باسكال للأعمدة والأسقف", "m3", "civil"),
    ("CONC-RC-40", "خرسانة مسلحة بمقاومة 40 ميجا باسكال للهياكل الإنشائية", "m3", "civil"),
    ("CONC-PLAIN-20", "خرسانة عادية بمقاومة 20 ميجا باسكال", "m3", "civil"),
    ("STEEL-REBAR-Y08", "حديد تسليح قطر 8 مم", "ton", "civil"),
    ("STEEL-REBAR-Y10", "حديد تسليح قطر 10 مم", "ton", "civil"),
    ("STEEL-REBAR-Y12", "حديد تسليح قطر 12 مم", "ton", "civil"),
    ("STEEL-REBAR-Y16", "حديد تسليح قطر 16 مم", "ton", "civil"),
    ("STEEL-REBAR-Y20", "حديد تسليح قطر 20 مم", "ton", "civil"),
    ("STEEL-REBAR-Y25", "حديد تسليح قطر 25 مم", "ton", "civil"),
    ("BLOCK-CONC-20", "بلوك خرساني قياس 20 سم", "m2", "civil"),
    ("BLOCK-CONC-15", "بلوك خرساني قياس 15 سم", "m2", "civil"),
    ("EXC-FOUND", "أعمال حفر للأساسات", "m3", "civil"),
    ("BACKFILL", "ردم وتسوية", "m3", "civil"),
    ("PAINT-INT-PLST", "دهان بلاستيكي داخلي درجة أولى", "m2", "finishing"),
    ("PAINT-EXT-WTH", "دهان خارجي مقاوم للعوامل الجوية", "m2", "finishing"),
    ("TILE-PORC-60", "بلاط بورسلين 60×60 سم", "m2", "finishing"),
    ("TILE-CER-WALL", "بلاط سيراميك للحوائط", "m2", "finishing"),
    ("MARBLE-FLOOR", "رخام للأرضيات", "m2", "finishing"),
    ("GYPSUM-CEIL", "جبس بورد للسقوف المعلقة", "m2", "finishing"),
    ("FURN-DESK-EXEC", "مكتب تنفيذي قياس كبير", "no", "furniture"),
    ("FURN-DESK-STAFF", "مكتب موظف قياس متوسط", "no", "furniture"),
    ("FURN-CHAIR-EXEC", "كرسي تنفيذي جلد طبيعي", "no", "furniture"),
    ("FURN-CHAIR-STAFF", "كرسي موظف دوار", "no", "furniture"),
    ("FURN-SOFA-3S", "كنبة ثلاثية للاستقبال", "no", "furniture"),
    ("FURN-TABLE-CONF", "طاولة اجتماعات للقاعات", "no", "furniture"),
    ("FURN-CAB-FILE", "خزانة ملفات معدنية", "no", "furniture"),
    ("FURN-STUDENT-DESK", "مكتب طالب مدرسي", "no", "furniture"),
    ("FURN-STUDENT-CHAIR", "كرسي طالب مدرسي", "no", "furniture"),
    ("AC-SPLIT-2T", "مكيف سبليت 24000 وحدة", "no", "mep"),
    ("AC-SPLIT-3T", "مكيف سبليت 36000 وحدة", "no", "mep"),
    ("AC-PKG-5T", "مكيف باكدج 60000 وحدة", "no", "mep"),
    ("ELEC-WIRE-2.5", "سلك كهرباء 2.5 مم", "m", "mep"),
    ("ELEC-WIRE-4", "سلك كهرباء 4 مم", "m", "mep"),
    ("ELEC-SWITCH", "مفتاح إنارة عادي", "no", "mep"),
    ("ELEC-SOCKET", "مقبس كهرباء 13 أمبير", "no", "mep"),
    ("LIGHT-LED-PNL", "لوحة إنارة LED قياس 60×60", "no", "mep"),
    ("PLUMB-PIPE-PPR-25", "أنبوب PPR قياس 25 مم", "m", "mep"),
    ("PLUMB-PIPE-PPR-32", "أنبوب PPR قياس 32 مم", "m", "mep"),
    ("DOOR-WOOD-INT", "باب خشبي داخلي", "no", "finishing"),
    ("DOOR-STEEL-EXT", "باب حديد خارجي", "no", "finishing"),
    ("WINDOW-ALUM", "نافذة ألمنيوم مع زجاج", "m2", "finishing"),
    ("CLEAN-DAILY", "خدمة نظافة يومية للمباني", "lump", "other"),
    ("SEC-GUARD", "حارس أمن شهرياً", "no", "other"),
    ("MAINT-AC-MONTH", "صيانة مكيفات شهرياً", "no", "other"),
]


def upsert_regions(db: Session) -> None:
    existing_codes = {
        r for (r,) in db.execute(select(Region.code))
    }
    for code, name_ar, name_en in REGIONS:
        if code in existing_codes:
            continue
        db.add(Region(code=code, name_ar=name_ar, name_en=name_en))


def upsert_cities(db: Session) -> None:
    code_to_id = {
        code: id_
        for code, id_ in db.execute(select(Region.code, Region.id))
    }
    existing = {c for (c,) in db.execute(select(City.code))}
    for code, name_ar, region_code in CITIES:
        if code in existing:
            continue
        db.add(
            City(
                code=code,
                name_ar=name_ar,
                region_id=code_to_id.get(region_code),
            )
        )


def upsert_sectors(db: Session) -> None:
    db.flush()
    existing = {
        c: i for c, i in db.execute(select(Sector.code, Sector.id))
    }
    # two passes: top-level first, then children
    for code, name_ar, name_en, parent in SECTORS:
        if parent is None and code not in existing:
            db.add(Sector(code=code, name_ar=name_ar, name_en=name_en))
    db.flush()
    existing = {c: i for c, i in db.execute(select(Sector.code, Sector.id))}
    for code, name_ar, name_en, parent in SECTORS:
        if parent is not None and code not in existing:
            db.add(
                Sector(
                    code=code,
                    name_ar=name_ar,
                    name_en=name_en,
                    parent_id=existing.get(parent),
                )
            )


def upsert_government_entities(db: Session) -> None:
    existing = {c for (c,) in db.execute(select(GovernmentEntity.code))}
    for code, name_ar, name_en, sector_type in GOVERNMENT_ENTITIES:
        if code in existing:
            continue
        db.add(
            GovernmentEntity(
                code=code,
                name_ar=name_ar,
                name_en=name_en,
                sector_type=sector_type,
            )
        )


def upsert_master_items(db: Session) -> None:
    existing = {c for (c,) in db.execute(select(MasterItem.code))}
    for code, name_ar, unit, _category in INITIAL_MASTER_ITEMS:
        if code in existing:
            continue
        db.add(
            MasterItem(
                code=code,
                name_ar=name_ar,
                default_unit=unit,
            )
        )


def main() -> int:
    configure_logging()
    LOG.info("seed_starting")
    db = SessionLocal()
    try:
        upsert_regions(db)
        upsert_cities(db)
        upsert_sectors(db)
        upsert_government_entities(db)
        upsert_master_items(db)
        db.commit()
        LOG.info(
            "seed_complete",
            regions=len(REGIONS),
            cities=len(CITIES),
            sectors=len(SECTORS),
            entities=len(GOVERNMENT_ENTITIES),
            master_items=len(INITIAL_MASTER_ITEMS),
        )
    except Exception as exc:
        db.rollback()
        LOG.error("seed_failed", error=str(exc))
        raise
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
