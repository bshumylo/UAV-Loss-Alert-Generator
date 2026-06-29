#!/usr/bin/env python3
"""
Вбудовує settlements.json у Report_2.0.html (замінює рядок `const settlementsDB = [...]`).
Запуск (після fetch_settlements.py):  python embed_settlements.py
Залишає лише потрібні застосунку поля: name_uk, oblast, lat, lon.
"""
import json, re, sys, os

HTML = "Report_2.0.html"
SRC  = "settlements.json"

def main():
    if not os.path.exists(SRC):
        sys.exit(f"Немає {SRC}. Спочатку запустіть fetch_settlements.py")
    db = json.load(open(SRC, encoding="utf-8"))
    slim = [{"name_uk": s["name_uk"], "oblast": s["oblast"],
             "lat": round(s["lat"], 6), "lon": round(s["lon"], 6)} for s in db]
    js = "const settlementsDB = " + json.dumps(slim, ensure_ascii=False, separators=(",", ":")) + ";"

    html = open(HTML, encoding="utf-8").read()
    new, n = re.subn(r"const settlementsDB = \[.*?\];", lambda m: js, html, count=1, flags=re.S)
    if n == 0:
        sys.exit("Не знайдено рядок `const settlementsDB = [...]` у HTML")
    open(HTML, "w", encoding="utf-8").write(new)

    obl = {}
    for s in slim:
        obl[s["oblast"]] = obl.get(s["oblast"], 0) + 1
    print(f"Вбудовано {len(slim)} НП у {HTML}")
    for k, v in sorted(obl.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
