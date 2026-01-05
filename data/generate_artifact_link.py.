from pathlib import Path

# --------------------------
# Cartella output dentro 'data'
# --------------------------
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
HTML_FILE = OUTPUT_DIR / "latest_artifact.html"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------
# Trova l'ultimo file XLSX
# --------------------------
xlsx_files = sorted(
    OUTPUT_DIR.glob("*.xlsx"),
    key=lambda f: f.stat().st_mtime,
    reverse=True
)

if not xlsx_files:
    raise RuntimeError("❌ Nessun file XLSX trovato in data/output")

latest_file = xlsx_files[0]

# --------------------------
# HTML (LINK RELATIVO)
# --------------------------
html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Ultimo Artifact</title>
</head>
<body>
    <h2>Ultimo file generato</h2>
    <p>
        <a href="{latest_file.name}" download>
            {latest_file.name}
        </a>
    </p>
</body>
</html>
"""

HTML_FILE.write_text(html_content, encoding="utf-8")

print(f"✅ HTML generato: {HTML_FILE}")
print(f"📄 File puntato: {latest_file.name}")
