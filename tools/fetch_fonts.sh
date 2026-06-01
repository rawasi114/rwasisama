#!/usr/bin/env bash
# تنزيل خط Cairo الحر (بديل عملي قابل للتضمين) إلى rawasi_base/static/src/fonts.
# يتطلب اتصالاً بالشبكة. للإنتاج، استبدله/أكمله بخطوط العلامة المرخّصة
# (DIN Next LT Arabic / GE SS Two).
set -euo pipefail

DEST="$(cd "$(dirname "$0")/.." && pwd)/rawasi_base/static/src/fonts"
mkdir -p "$DEST"

base="https://github.com/google/fonts/raw/main/ofl/cairo/static"
echo "Downloading Cairo into: $DEST"
curl -fL "$base/Cairo-Regular.ttf" -o "$DEST/Cairo-Regular.ttf"
curl -fL "$base/Cairo-Bold.ttf"    -o "$DEST/Cairo-Bold.ttf"

echo "Done. Next steps:"
echo "  1) add the two .ttf paths to web.report_assets_common in rawasi_base/__manifest__.py"
echo "  2) enable the @font-face rules in rawasi_base/static/src/scss/rawasi_report.scss"
