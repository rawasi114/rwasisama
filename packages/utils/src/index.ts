/**
 * Light Arabic normalization for headers and descriptions (SPEC Appendix A.8).
 * Trims, collapses whitespace, unifies hamza/alef-maqsura/taa-marbuta.
 * Keeps internal spaces (used for full-text search and header matching).
 */
export function normalizeArabicLight(text: string): string {
  return (text ?? '')
    .trim()
    .replace(/\s+/g, ' ')
    .replace(/[آأإ]/g, 'ا')
    .replace(/ى/g, 'ي')
    .replace(/ة/g, 'ه');
}

/**
 * Strong normalization for unit-symbol matching (SPEC Appendix A.5 / units_lookup).
 * Steps: trim, collapse whitespace, replace punctuation with space, lowercase,
 * unify hamza/alef-maqsura/taa-marbuta, then remove ALL spaces.
 *
 * Examples: "م . ط" -> "مط", "م/ط" -> "مط", "Sq. M" -> "sqm".
 */
export function normalizeUnit(text: string): string {
  return (text ?? '')
    .trim()
    .replace(/\s+/g, ' ')
    .replace(/[.\/_\-]/g, ' ')
    .toLowerCase()
    .replace(/[آأإ]/g, 'ا')
    .replace(/ى/g, 'ي')
    .replace(/ة/g, 'ه')
    .replace(/\s+/g, '');
}

/** Format a number as Saudi Riyal: "1,234.50 ر.س". */
export function formatSAR(amount: number): string {
  const formatted = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
  return `${formatted} ر.س`;
}

/** Saudi VAT rate (15%). */
export const VAT_RATE = 0.15;
