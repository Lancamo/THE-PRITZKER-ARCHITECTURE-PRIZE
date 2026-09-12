#!/usr/bin/env python3
"""A 数据官 · 生成 data/editions.json：V1.0 awards.json + 生卒年/作品坐标 富化表。

用法: python3 tools/make_editions.py

- 合并 1988 年的两条记录为一届（双得主）
- 为每位得主补 birth/death/name_en；为每届代表作补 city/country/lat/lng/title_en
- 坐标为公开地理信息的近似值，供点图定位（精度 ±10km 不影响叙事）
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT.parent / "V1.0" / "data" / "awards.json"
OUT = ROOT / "data" / "editions.json"

# 富化表：年份 → (得主英文名与生卒 [按原数据顺序], 代表作坐标)
# (title_en, city, country, lat, lng)
ENRICH: dict[int, dict] = {
    1979: {"en": [("Philip Johnson", 1906, 2005)], "work": ("Glass House", "New Canaan", "美国", 41.14, -73.49)},
    1980: {"en": [("Luis Barragán", 1902, 1988)], "work": ("Torres de Satélite", "墨西哥城", "墨西哥", 19.49, -99.24)},
    1981: {"en": [("James Stirling", 1926, 1992)], "work": ("Seeley Historical Library", "剑桥", "英国", 52.20, 0.12)},
    1982: {"en": [("Kevin Roche", 1922, 2019)], "work": ("Knights of Columbus Building", "纽黑文", "美国", 41.30, -72.93)},
    1983: {"en": [("I. M. Pei", 1917, 2019)], "work": ("East Building, National Gallery of Art", "华盛顿", "美国", 38.89, -77.02)},
    1984: {"en": [("Richard Meier", 1934, None)], "work": ("High Museum of Art", "亚特兰大", "美国", 33.79, -84.39)},
    1985: {"en": [("Hans Hollein", 1934, 2014)], "work": ("Museum Abteiberg", "门兴格拉德巴赫", "德国", 51.19, 6.44)},
    1986: {"en": [("Gottfried Böhm", 1920, 2021)], "work": ("Bensberg Civic Centre", "贝吉施格拉德巴赫", "德国", 50.99, 7.13)},
    1987: {"en": [("Kenzo Tange", 1913, 2005)], "work": ("St. Mary's Cathedral", "东京", "日本", 35.71, 139.72)},
    1988: {
        "en": [("Gordon Bunshaft", 1909, 1990), ("Oscar Niemeyer", 1907, 2012)],
        "works": [
            ("Beinecke Rare Book & Manuscript Library", "纽黑文", "美国", 41.31, -72.93, "拜内克珍本及手稿图书馆"),
            ("Cathedral of Brasília", "巴西利亚", "巴西", -15.80, -47.88, "巴西利亚大教堂"),
        ],
    },
    1989: {"en": [("Frank Gehry", 1929, None)], "work": ("Walt Disney Concert Hall", "洛杉矶", "美国", 34.06, -118.25)},
    1990: {"en": [("Aldo Rossi", 1931, 1997)], "work": ("Bundeskunsthalle", "波恩", "德国", 50.71, 7.12)},
    1991: {"en": [("Robert Venturi", 1925, 2018)], "work": ("Sainsbury Wing, National Gallery", "伦敦", "英国", 51.51, -0.13)},
    1992: {"en": [("Álvaro Siza", 1933, None)], "work": ("Portugal Pavilion, Expo 98", "里斯本", "葡萄牙", 38.77, -9.10)},
    1993: {"en": [("Fumihiko Maki", 1928, 2024)], "work": ("Tokyo Metropolitan Gymnasium", "东京", "日本", 35.68, 139.71)},
    1994: {"en": [("Christian de Portzamparc", 1944, None)], "work": ("French Embassy in Germany", "柏林", "德国", 52.52, 13.38)},
    1995: {"en": [("Tadao Ando", 1941, None)], "work": ("Church of the Light", "茨木", "日本", 34.81, 135.57)},
    1996: {"en": [("Rafael Moneo", 1937, None)], "work": ("Kursaal Palace", "圣塞巴斯蒂安", "西班牙", 43.32, -1.98)},
    1997: {"en": [("Sverre Fehn", 1924, 2009)], "work": ("Norwegian Glacier Museum", "菲耶兰", "挪威", 61.42, 6.76)},
    1998: {"en": [("Renzo Piano", 1937, None)], "work": ("Kansai International Airport", "大阪", "日本", 34.43, 135.23)},
    1999: {"en": [("Norman Foster", 1935, None)], "work": ("Millennium Bridge", "伦敦", "英国", 51.51, -0.10)},
    2000: {"en": [("Rem Koolhaas", 1944, None)], "work": ("Casa da Música", "波尔图", "葡萄牙", 41.16, -8.63)},
    2001: {"en": [("Herzog & de Meuron", 1950, None)], "work": ("Tate Modern", "伦敦", "英国", 51.51, -0.10)},
    2002: {"en": [("Glenn Murcutt", 1936, None)], "work": ("Berowra Waters Inn", "贝罗拉", "澳大利亚", -33.60, 151.15)},
    2003: {"en": [("Jørn Utzon", 1918, 2008)], "work": ("Sydney Opera House", "悉尼", "澳大利亚", -33.86, 151.22)},
    2004: {"en": [("Zaha Hadid", 1950, 2016)], "work": ("Bridge Pavilion", "萨拉戈萨", "西班牙", 41.66, -0.90)},
    2005: {"en": [("Thom Mayne", 1944, None)], "work": ("San Francisco Federal Building", "旧金山", "美国", 37.78, -122.41)},
    2006: {"en": [("Paulo Mendes da Rocha", 1928, 2021)], "work": ("Serra Dourada Stadium", "戈亚尼亚", "巴西", -16.70, -49.27)},
    2007: {"en": [("Richard Rogers", 1933, 2021)], "work": ("Lloyd's Building", "伦敦", "英国", 51.51, -0.08)},
    2008: {"en": [("Jean Nouvel", 1945, None)], "work": ("Torre Agbar", "巴塞罗那", "西班牙", 41.40, 2.19)},
    2009: {"en": [("Peter Zumthor", 1943, None)], "work": ("Therme Vals", "瓦尔斯", "瑞士", 46.62, 9.18)},
    2010: {"en": [("Kazuyo Sejima", 1956, None), ("Ryue Nishizawa", 1966, None)], "work": ("21st Century Museum of Contemporary Art", "金泽", "日本", 36.56, 136.66)},
    2011: {"en": [("Eduardo Souto de Moura", 1952, None)], "work": ("Estádio Municipal de Braga", "布拉加", "葡萄牙", 41.55, -8.43)},
    2012: {"en": [("Wang Shu", 1963, None)], "work": ("Ningbo Museum", "宁波", "中国", 29.86, 121.55)},
    2013: {"en": [("Toyo Ito", 1941, None)], "work": ("Sendai Mediatheque", "仙台", "日本", 38.27, 140.87)},
    2014: {"en": [("Shigeru Ban", 1957, None)], "work": ("Paper Dome", "神户", "日本", 34.66, 135.14)},
    2015: {"en": [("Frei Otto", 1925, 2015)], "work": ("Olympiastadion", "慕尼黑", "德国", 48.17, 11.55)},
    2016: {"en": [("Alejandro Aravena", 1967, None)], "work": ("UC Innovation Center", "圣地亚哥", "智利", -33.44, -70.63)},
    2017: {"en": [("Rafael Aranda", 1961, None), ("Carme Pigem", 1962, None), ("Ramon Vilalta", 1960, None)], "work": ("Sant Antoni Library", "巴塞罗那", "西班牙", 41.38, 2.17)},
    2018: {"en": [("B. V. Doshi", 1927, 2023)], "work": ("Indian Institute of Management", "班加罗尔", "印度", 12.97, 77.59)},
    2019: {"en": [("Arata Isozaki", 1931, 2022)], "work": ("Art Tower Mito", "水户", "日本", 36.37, 140.47)},
    2020: {"en": [("Yvonne Farrell", 1951, None), ("Shelley McNamara", 1952, None)], "work": ("Bocconi University", "米兰", "意大利", 45.45, 9.19)},
    2021: {"en": [("Anne Lacaton", 1955, None), ("Jean-Philippe Vassal", 1954, None)], "work": ("ENSA Nantes", "南特", "法国", 47.22, -1.55)},
    2022: {"en": [("Diébédo Francis Kéré", 1965, None)], "work": ("Centre for Earth Architecture", "莫普提", "马里", 14.50, -4.20)},
    2023: {"en": [("David Chipperfield", 1953, None)], "work": ("Neues Museum", "柏林", "德国", 52.52, 13.40)},
    2024: {"en": [("Riken Yamamoto", 1945, None)], "work": ("Yokosuka Museum of Art", "横须贺", "日本", 35.28, 139.67)},
    2025: {"en": [("Liu Jiakun", 1956, None)], "work": ("West Village", "成都", "中国", 30.67, 104.03)},
    2026: {"en": [("Smiljan Radić Clarke", 1965, None)], "work": ("Serpentine Pavilion 2014", "伦敦", "英国", 51.50, -0.17)},
}


def main() -> None:
    raw = json.loads(SRC.read_text(encoding="utf-8"))
    by_year: dict[int, dict] = {}
    for rec in raw["records"]:
        year = rec["year"]
        edition = by_year.setdefault(year, {"year": year, "laureates": [], "works": []})
        for l in rec["laureates"]:
            edition["laureates"].append(
                {"name_cn": l["name"], "nationalities": l["nationalities"]}
            )
        w = rec.get("work") or {}
        if w.get("title"):
            edition["works"].append(
                {"title_cn": w["title"], "completed": w.get("completed", "")}
            )

    editions = []
    for year in sorted(by_year):
        ed = by_year[year]
        info = ENRICH[year]
        ens = info["en"]
        assert len(ens) == len(ed["laureates"]), f"{year} 得主数不匹配"
        for i, (name_en, birth, death) in enumerate(ens):
            ed["laureates"][i]["name_en"] = name_en
            ed["laureates"][i]["birth_year"] = birth
            ed["laureates"][i]["death_year"] = death
            ed["laureates"][i]["age_at_award"] = year - birth if birth else None

        if "works" in info:  # 1988 特例：展平为逐作品富化
            filled = []
            for (title_en, city, country, lat, lng, title_cn) in info["works"]:
                match = next((w for w in ed["works"] if w["title_cn"] == title_cn), None)
                completed = match["completed"] if match else ""
                filled.append({
                    "title_cn": title_cn, "title_en": title_en, "city": city,
                    "country": country, "lat": lat, "lng": lng, "completed": completed,
                })
            ed["works"] = filled
        else:
            title_en, city, country, lat, lng = info["work"]
            ed["works"][0].update({
                "title_en": title_en, "city": city, "country": country,
                "lat": lat, "lng": lng,
            })
        editions.append(ed)

    payload = {
        "source": "V1.0/data/awards.json + 富化表（生卒年/坐标）",
        "fetched": raw.get("fetched", ""),
        "count": len(editions),
        "editions": editions,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    people = sum(len(e["laureates"]) for e in editions)
    print(f"生成 {OUT} · {len(editions)} 届 · {people} 位得主 · {OUT.stat().st_size/1024:.1f} KB")


if __name__ == "__main__":
    main()
