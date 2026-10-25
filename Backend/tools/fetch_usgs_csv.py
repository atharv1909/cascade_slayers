import urllib.request, os

url = "https://earthquake.usgs.gov/fdsnws/event/1/query?format=csv&starttime=2018-01-01&endtime=2023-12-31&minmagnitude=4.5&limit=5000"
out_dir = r"D:\Cascade_slayers\data\earthquake_database"
os.makedirs(out_dir, exist_ok=True)
out_file = os.path.join(out_dir, "earthquakes.csv")

try:
    print("Fetching real USGS earthquake data...")
    urllib.request.urlretrieve(url, out_file)
    size = os.path.getsize(out_file)
    print(f"Success! Saved real USGS catalog: {out_file} ({size:,} bytes)")
    with open(out_file, "r", encoding="utf-8") as f:
        lines = [f.readline().strip() for _ in range(5)]
    for l in lines:
        print("  ", l)
except Exception as e:
    print(f"Error fetching USGS: {e}")
