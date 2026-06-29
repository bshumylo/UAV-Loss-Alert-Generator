import geopandas as gpd
import osmnx as ox
import pandas as pd

# -----------------------------------------
# Налаштування
# -----------------------------------------

regions = [
    "Донецька область, Україна",
    "Дніпропетровська область, Україна",
    "Луганська область, Україна",
    "Харківська область, Україна",
    "Запорізька область, Україна",
    "Сумська область, Україна",
]

tags = {
    "place": [
        "city",
        "town",
        "village",
        "hamlet",
    ]
}

all_places = []

for region in regions:
    print(region)

    gdf = ox.features_from_place(region, tags)

    gdf = gdf[
        gdf["place"].isin(["city", "town", "village", "hamlet"])
    ]

    gdf = gdf[gdf.geometry.geom_type == "Point"]

    gdf["lat"] = gdf.geometry.y
    gdf["lon"] = gdf.geometry.x

    gdf["region"] = region.replace(", Україна", "")

    all_places.append(
        gdf[
            [
                "lat",
                "lon",
                "name",
                "region",
            ]
        ]
    )

result = pd.concat(all_places)

result = result.drop_duplicates()

result = result.sort_values(
    ["region", "name"]
)

result.to_csv(
    "places.csv",
    index=False,
    encoding="utf-8-sig"
)

print(result.head())

print()
print("Done.")
print(len(result), "places")