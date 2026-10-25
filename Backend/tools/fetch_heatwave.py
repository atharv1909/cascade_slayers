import urllib.request, json, os, pandas as pd

url = "https://archive-api.open-meteo.com/v1/archive?latitude=28.61&longitude=77.20&start_date=2024-05-15&end_date=2024-06-25&hourly=temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m"
out_dir = r"D:\Cascade_slayers\data\weather"
os.makedirs(out_dir, exist_ok=True)
out_file = os.path.join(out_dir, "delhi_heatwave_2024_hourly.csv")

try:
    print("Fetching real Delhi 2024 extreme heatwave hourly data...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    hourly = data.get("hourly", {})
    df = pd.DataFrame(hourly)
    df.to_csv(out_file, index=False)
    print(f"Success! Saved real heatwave data: {out_file} ({len(df)} hourly rows, {os.path.getsize(out_file):,} bytes)")
    print(f"Max temperature recorded: {df['temperature_2m'].max()} C")
except Exception as e:
    print(f"Error: {e}")
