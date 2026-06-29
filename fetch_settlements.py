#!/usr/bin/env python3
"""
Завантаження координат населених пунктів українських областей через Overpass API.
v3 — дедублікація (relation > way > node), відфільтровані типи місць.
"""

import requests
import json
import csv
import time
from math import radians, cos, sin, sqrt, atan2
from datetime import datetime
from collections import Counter

# ══════════════════════════════════════════════════════════
# КОНФІГУРАЦІЯ
# ══════════════════════════════════════════════════════════

OBLASTS = [
    {"name_uk": "Донецька",         "osm_name": "Donetsk Oblast"},
    {"name_uk": "Дніпропетровська", "osm_name": "Dnipropetrovsk Oblast"},
    {"name_uk": "Запорізька",       "osm_name": "Zaporizhzhia Oblast"},
    {"name_uk": "Луганська",        "osm_name": "Luhansk Oblast"},
    {"name_uk": "Харківська",       "osm_name": "Kharkiv Oblast"},
    {"name_uk": "Сумська",          "osm_name": "Sumy Oblast"},
    {"name_uk": "Чернігівська",     "osm_name": "Chernihiv Oblast"},
    {"name_uk": "Херсонська",       "osm_name": "Kherson Oblast"},
    {"name_uk": "Миколаївська",     "osm_name": "Mykolaiv Oblast"},
    {"name_uk": "Одеська",          "osm_name": "Odessa Oblast"},
    # {"name_uk": "Київська",         "osm_name": "Kyiv Oblast"},
]

# Тільки реальні адміністративні одиниці — без suburb/locality
PLACE_TYPES = "city|town|village|hamlet"

# Радіус дедублікації в метрах
DEDUP_RADIUS_M = 500

# Резервні Overpass endpoints
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

OUTPUT_JSON = "settlements.json"
OUTPUT_CSV  = "settlements.csv"

HEADERS = {
    "User-Agent":   "SettlementFetcher/3.0 (ua-settlements-project)",
    "Accept":       "application/json, text/plain, */*",
    "Content-Type": "application/x-www-form-urlencoded",
}

# Маппінг EN → UK назв областей для OSM
OBLAST_UK_NAMES = {
    "Donetsk Oblast":        "Донецька область",
    "Dnipropetrovsk Oblast": "Дніпропетровська область",
    "Zaporizhzhia Oblast":   "Запорізька область",
    "Luhansk Oblast":        "Луганська область",
    "Kharkiv Oblast":        "Харківська область",
    "Kherson Oblast":        "Херсонська область",
    "Mykolaiv Oblast":       "Миколаївська область",
    "Odessa Oblast":         "Одеська область",
    "Kyiv Oblast":           "Київська область",
}

# Пріоритет OSM-типу при дедублікації (менше = вищий пріоритет)
OSM_TYPE_PRIORITY = {"relation": 0, "way": 1, "node": 2}

# ══════════════════════════════════════════════════════════
# OVERPASS: ЗАПИТ І ОТРИМАННЯ ДАНИХ
# ══════════════════════════════════════════════════════════

def build_query(osm_name: str) -> str:
    """Overpass QL — шукає по UK та EN назві області."""
    uk_name = OBLAST_UK_NAMES.get(osm_name, "")
    if uk_name:
        area_clause = (
            f'(area["name:uk"="{uk_name}"]["admin_level"="4"];'
            f' area["name:en"="{osm_name}"]["admin_level"="4"];)'
            f'->.searchArea;'
        )
    else:
        area_clause = f'area["name:en"="{osm_name}"]["admin_level"="4"]->.searchArea;'

    return (
        f'[out:json][timeout:180];\n'
        f'{area_clause}\n'
        f'(\n'
        f'  node["place"~"^({PLACE_TYPES})$"](area.searchArea);\n'
        f'  way["place"~"^({PLACE_TYPES})$"](area.searchArea);\n'
        f'  relation["place"~"^({PLACE_TYPES})$"](area.searchArea);\n'
        f');\n'
        f'out center tags;\n'
    )


def post_with_retry(query: str, max_retries: int = 3) -> dict | None:
    """Надсилає запит, перебираючи endpoints. Обробляє 429 і таймаути."""
    for endpoint in OVERPASS_ENDPOINTS:
        for attempt in range(1, max_retries + 1):
            try:
                print(f"    → {endpoint}  (спроба {attempt}/{max_retries})")
                resp = requests.post(
                    endpoint,
                    data={"data": query},
                    headers=HEADERS,
                    timeout=200,
                )
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 429:
                    wait = 30 * attempt
                    print(f"    ⚠️  Rate limit — чекаємо {wait}с...")
                    time.sleep(wait)
                elif resp.status_code == 504:
                    print(f"    ⚠️  Server timeout (504) — пробуємо інший endpoint...")
                    break
                else:
                    print(f"    ❌ HTTP {resp.status_code}: {resp.text[:200]}")
                    break
            except requests.exceptions.Timeout:
                print(f"    ⚠️  Client timeout (спроба {attempt})...")
                time.sleep(10)
            except requests.exceptions.RequestException as e:
                print(f"    ❌ Мережева помилка: {e}")
                break
        time.sleep(5)
    return None


# ══════════════════════════════════════════════════════════
# ПАРСИНГ
# ══════════════════════════════════════════════════════════

def parse_elements(elements: list, oblast_name: str) -> list[dict]:
    """Перетворює OSM-елементи у плоскі записи."""
    results = []
    for el in elements:
        tags = el.get("tags", {})

        if el["type"] == "node":
            lat, lon = el.get("lat"), el.get("lon")
        else:
            center = el.get("center", {})
            lat, lon = center.get("lat"), center.get("lon")

        if lat is None or lon is None:
            continue

        name = (
            tags.get("name:uk")
            or tags.get("name")
            or tags.get("name:en")
            or ""
        )

        results.append({
            "name_uk":  name,
            "name_en":  tags.get("name:en", ""),
            "place":    tags.get("place", ""),
            "oblast":   oblast_name,
            "lat":      round(lat, 6),
            "lon":      round(lon, 6),
            "osm_id":   el.get("id"),
            "osm_type": el["type"],
        })
    return results


# ══════════════════════════════════════════════════════════
# ДЕДУБЛІКАЦІЯ
# ══════════════════════════════════════════════════════════

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Відстань між двома точками у метрах (формула Гаверсинуса)."""
    R = 6_371_000
    φ1, φ2 = radians(lat1), radians(lat2)
    dφ = radians(lat2 - lat1)
    dλ = radians(lon2 - lon1)
    a = sin(dφ / 2) ** 2 + cos(φ1) * cos(φ2) * sin(dλ / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def deduplicate(records: list[dict], radius_m: float = DEDUP_RADIUS_M) -> list[dict]:
    """
    Видаляє дублікати одного населеного пункту (node/way/relation).

    Алгоритм:
    1. Сортуємо: relation → way → node (вищий пріоритет першим).
    2. Для кожного запису перевіряємо, чи є вже збережений запис
       з тією ж назвою, тією ж областю і в межах radius_m метрів.
    3. Якщо є — пропускаємо (це дублікат).
    """
    sorted_recs = sorted(
        records,
        key=lambda r: OSM_TYPE_PRIORITY.get(r["osm_type"], 9)
    )

    kept: list[dict] = []
    # Індекс для швидшого пошуку: oblast -> list of kept records
    index: dict[str, list[dict]] = {}

    for rec in sorted_recs:
        oblast = rec["oblast"]
        name   = rec["name_uk"]
        is_dup = False

        for k in index.get(oblast, []):
            if k["name_uk"] != name:
                continue
            dist = haversine_m(k["lat"], k["lon"], rec["lat"], rec["lon"])
            if dist < radius_m:
                is_dup = True
                break

        if not is_dup:
            kept.append(rec)
            index.setdefault(oblast, []).append(rec)

    return kept


# ══════════════════════════════════════════════════════════
# ЗБЕРЕЖЕННЯ
# ══════════════════════════════════════════════════════════

def save_json(records: list, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"💾 JSON: {path}  ({len(records)} записів)")


def save_csv(records: list, path: str):
    if not records:
        return
    fields = ["name_uk", "name_en", "place", "oblast", "lat", "lon", "osm_id", "osm_type"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(records)
    print(f"💾 CSV:  {path}  ({len(records)} записів)")


# ══════════════════════════════════════════════════════════
# ГОЛОВНА ФУНКЦІЯ
# ══════════════════════════════════════════════════════════

def fetch_oblast(oblast: dict) -> list[dict]:
    print(f"\n⏳ {oblast['name_uk']} ({oblast['osm_name']})...")
    data = post_with_retry(build_query(oblast["osm_name"]))
    if data is None:
        print(f"  ❌ Не вдалося отримати дані")
        return []
    raw = parse_elements(data.get("elements", []), oblast["name_uk"])
    deduped = deduplicate(raw)
    removed = len(raw) - len(deduped)
    print(f"  ✅ Отримано: {len(raw)}  →  після дедублікації: {len(deduped)}  (−{removed} дублікатів)")
    return deduped


def print_stats(records: list):
    print("\n📈 По областях:")
    for name, cnt in sorted(Counter(r["oblast"] for r in records).items()):
        print(f"   {name:<25} {cnt:>5}")

    print("\n📈 По типах:")
    for place, cnt in sorted(Counter(r["place"] for r in records).items(), key=lambda x: -x[1]):
        print(f"   {place:<12} {cnt:>5}")


def main():
    print("═" * 60)
    print("  Населені пункти України — Overpass API  v3")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("═" * 60)

    all_records: list[dict] = []
    failed: list[str] = []

    for i, oblast in enumerate(OBLASTS):
        records = fetch_oblast(oblast)
        if records:
            all_records.extend(records)
        else:
            failed.append(oblast["name_uk"])

        if i < len(OBLASTS) - 1:
            print("  ⏸  Пауза 5с...")
            time.sleep(5)

    print(f"\n{'═'*60}")
    print(f"📊 Всього записів: {len(all_records)}")

    if failed:
        print(f"⚠️  Не завантажено: {', '.join(failed)}")

    save_json(all_records, OUTPUT_JSON)
    save_csv(all_records, OUTPUT_CSV)
    print_stats(all_records)


if __name__ == "__main__":
    main()