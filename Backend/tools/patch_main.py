with open('D:/B.Tech/Hackathons/Cascade/Backend/api/main.py', 'r', encoding='utf-8') as f:
    text = f.read()

root_handler = '''@app.get("/")
def root():
    ui_index = os.path.join(engine.root_dir, "ui", "index.html")
    if os.path.exists(ui_index):
        from fastapi.responses import FileResponse
        return FileResponse(ui_index)
    return {
        "title": "The 72-Hour Warning (Cascade_slayers) API",
        "status": "ONLINE",
        "docs": "/docs",
        "health": "/healthz",
        "scenarios": "/demo/scenarios",
        "risk": "/v1/risk"
    }

# Health and Ops endpoints
@app.get("/healthz")'''

text = text.replace('# Health and Ops endpoints\n@app.get("/healthz")', root_handler)
with open('D:/B.Tech/Hackathons/Cascade/Backend/api/main.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Updated main.py with root handler')
