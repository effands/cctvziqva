import urllib.request
import re

url = 'https://cctv.jogjakota.go.id/home'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')

scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', html, re.IGNORECASE)
print("Scripts found:", len(scripts))

for s in scripts:
    print(" ->", s)

# Print inline scripts
inline = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
print("\nInline Scripts found:", len(inline))
for i, code in enumerate(inline):
    if code.strip():
        print(f"--- Inline #{i+1} ---")
        print(code.strip()[:500])
