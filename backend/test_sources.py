import urllib.request, ssl, re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request(
    'https://www.basketball-reference.com/contracts/players.html',
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0'}
)
with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
    html = r.read().decode('utf-8')

# Find a chunk around a player link to understand the structure
idx = html.find('/players/j/jamesle01.html')
if idx < 0:
    idx = html.find('/players/')
print("player link at:", idx)
print("surrounding HTML (300 chars):")
print(html[max(0,idx-100):idx+300])
print()

# Also show the section around dollar amounts
idx2 = html.find('$154,647,000')
print("big salary at:", idx2)
print(html[max(0,idx2-300):idx2+100])
