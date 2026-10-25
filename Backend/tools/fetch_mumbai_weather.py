import urllib.request, json, os, pandas as pd

url = "https://archive-api.open-meteo.com/v1/archive?latitude=19.076&longitude=72.877&start_date=2023-06-01&end_date=2023-09-30&hourly=temperature_2m,relative_humidity_2m,precipitation,rain,wind_speed_10m"
out_dir = r"D:\Cascade_slayers\data\weather"
os.makedirs(out_dir, exist_ok=True)
out_file = os.path.join(out_dir, "mumbai_monsoon_2023_hourly.csv")

try:
    print("Fetching real Mumbai 2023 monsoon hourly weather from Open-Meteo archive...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    hourly = data.get("hourly", {})
    df = pd.DataFrame(hourly)
    df.to_csv(out_file, index=False)
    print(f"Success! Saved real Mumbai monsoon data: {out_file} ({len(df)} hourly rows, {os.path.getsize(out_file):,} bytes)")
    print(df.head(3))
except Exception as e:
    print(f"Error: {e}")
