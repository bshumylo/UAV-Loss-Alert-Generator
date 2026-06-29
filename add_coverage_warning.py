# -*- coding: utf-8 -*-
# add_coverage_warning.py
# Adds an out-of-coverage warning to Report_2.0.html.
# Run in the project folder:  python add_coverage_warning.py
# Idempotent: each replace is count=1 and keyed to unique text.

h = open("Report_2.0.html", encoding="utf-8").read()

# 1) CSS: yellow warn class
h = h.replace(
    ".geo-status.err { color: #e53935; }",
    ".geo-status.err { color: #e53935; }\n        .geo-status.warn { color: #f9a825; }",
    1)

# 2) Coverage threshold (km). Beyond it -> warning, no auto-fill.
h = h.replace(
    "        // Відстань між двома точками у км (Haversine)",
    "        const COVERAGE_RADIUS_KM = 25;\n\n        // Відстань між двома точками у км (Haversine)",
    1)

# 3) setGeoStatus: add 'warn' branch
h = h.replace(
"""            } else if (type === 'err') {
                el.innerHTML = '✗ ' + msg;
            } else {""",
"""            } else if (type === 'err') {
                el.innerHTML = '✗ ' + msg;
            } else if (type === 'warn') {
                el.innerHTML = '⚠ ' + msg;
            } else {""",
    1)

# 4) findNearestLocal: outOfCoverage flag instead of distKm
h = h.replace(
"""                oblast: OBLAST_SHORT_MAP[best.oblast] || best.oblast,
                distKm: bestDist
            };""",
"""                oblast: OBLAST_SHORT_MAP[best.oblast] || best.oblast,
                outOfCoverage: bestDist > COVERAGE_RADIUS_KM
            };""",
    1)

# 5) Geocoding: warn + no auto-fill outside coverage; drop distance display
h = h.replace(
"""            const local = findNearestLocal(lat, lon);
            if (local) {
                const locationValue = `${local.name.toUpperCase()}, ${local.oblast}`;
                document.getElementById('location').value = locationValue;
                setGeoStatus('ok', `${local.name} — знайдено локально (${local.distKm.toFixed(1)} км)`);
                return;
            }""",
"""            const local = findNearestLocal(lat, lon);
            if (local) {
                if (local.outOfCoverage) {
                    setGeoStatus('warn', 'Координати не належать до охоплених областей — заповніть населений пункт вручну');
                    return;
                }
                const locationValue = `${local.name.toUpperCase()}, ${local.oblast}`;
                document.getElementById('location').value = locationValue;
                setGeoStatus('ok', `${local.name} — знайдено локально`);
                return;
            }""",
    1)

open("Report_2.0.html", "w", encoding="utf-8").write(h)
print("Попередження додано")
