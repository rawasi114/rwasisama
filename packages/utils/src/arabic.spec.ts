import { normalizeArabicLight, normalizeUnit, formatSAR } from './index';

describe('normalizeArabicLight', () => {
  it('trims and collapses whitespace', () => {
    expect(normalizeArabicLight('  وصف   البند  ')).toBe('وصف البند');
  });

  it('unifies hamza variants and taa-marbuta', () => {
    expect(normalizeArabicLight('خرسانة')).toBe('خرسانه');
    expect(normalizeArabicLight('إجمالي')).toBe('اجمالي');
    expect(normalizeArabicLight('مأخذ')).toBe('ماخذ');
  });

  it('handles null/undefined safely', () => {
    expect(normalizeArabicLight(undefined as unknown as string)).toBe('');
  });
});

describe('normalizeUnit', () => {
  it('maps all linear-meter spellings to the same token', () => {
    const target = normalizeUnit('م.ط');
    expect(normalizeUnit('م ط')).toBe(target);
    expect(normalizeUnit('م/ط')).toBe(target);
    expect(normalizeUnit('م . ط')).toBe(target);
    expect(target).toBe('مط');
  });

  it('lowercases english unit text', () => {
    expect(normalizeUnit('Sq. M')).toBe('sqm');
    expect(normalizeUnit('LM')).toBe('lm');
  });

  it('keeps square-meter superscript distinct from plain 2 (resolved via aliases)', () => {
    // SPEC: م² and م2 are separate aliases of SQM, not collapsed by normalization.
    expect(normalizeUnit('م²')).toBe('م²');
    expect(normalizeUnit('م2')).toBe('م2');
  });
});

describe('formatSAR', () => {
  it('formats with thousands separator and 2 decimals', () => {
    expect(formatSAR(1234.5)).toBe('1,234.50 ر.س');
    expect(formatSAR(0)).toBe('0.00 ر.س');
  });
});
