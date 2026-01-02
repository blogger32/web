import os
import requests

# Куди зберігаємо (папка JS вашого проекту)
output_dir = os.path.join('main', 'static', 'main', 'js')

# Прямі посилання на файли бібліотеки
files = {
    "pdf.min.js": "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js",
    "pdf.worker.min.js": "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js"
}

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

print("Downloading PDF.js libraries...")

for filename, url in files.items():
    filepath = os.path.join(output_dir, filename)
    print(f"Downloading {filename}...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            f.write(response.content)
        print(f"Success: {filepath}")
    except Exception as e:
        print(f"Error downloading {filename}: {e}")

print("Done!")