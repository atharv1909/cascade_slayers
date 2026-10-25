# Assemble script
import os
import json

# 1. Load city geojson data
city_files = ['zones', 'water', 'drains', 'roads', 'facilities', 'substations', 'buildings', 'landuse']
city_data = {}
for cf in city_files:
    p = f"D:/B.Tech/Hackathons/Cascade/UI/the_72_hour_warning/ui/data/city/{cf}.geojson"
    with open(p, "r", encoding="utf-8") as f:
        city_data[cf] = json.load(f)

# 2. Load mock data
mock_files = ['scenarios', 'risk', 'cascade', 'graph']
mock_data = {}
for mf in mock_files:
    p = f"D:/B.Tech/Hackathons/Cascade/UI/the_72_hour_warning/ui/mock/{mf}.json"
    with open(p, "r", encoding="utf-8") as f:
        mock_data[mf] = json.load(f)

city_line = "window.CITY_DATA = " + json.dumps(city_data, separators=(',', ':')) + ";"
mock_line = "window.MOCK_BUNDLE = " + json.dumps(mock_data, separators=(',', ':')) + ";"

# 3. Load UI head & core logic
with open("D:/B.Tech/Hackathons/Cascade/tools/ui_core.js", "r", encoding="utf-8") as f:
    ui_core_js = f.read()

with open("D:/B.Tech/Hackathons/Cascade/tools/ui_head.html", "r", encoding="utf-8") as f:
    ui_head_html = f.read()

final_html = ui_head_html + "\n<script>\n" + city_line + "\n" + mock_line + "\n</script>\n" + ui_core_js + "\n</body>\n</html>"

out_paths = [
    "D:/B.Tech/Hackathons/Cascade/UI/index.html",
    "D:/B.Tech/Hackathons/Cascade/UI/the_72_hour_warning/ui/index.html",
    "D:/B.Tech/Hackathons/Cascade/Backend/ui/index.html"
]

for p in out_paths:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as out:
        out.write(final_html)
    print(f"Successfully generated {p} ({len(final_html)} chars)")
