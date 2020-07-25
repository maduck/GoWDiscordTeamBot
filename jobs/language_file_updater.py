import gzip

import requests

languages = (
    'English',
    'French',
    'German',
    'Italian',
    'Russian',
    'Spanish',
    'Chinese',
)
base_url = 'https://gemsofwarconsole.blob.core.windows.net/data/Production500/Localization'

for lang in languages:
    filename = f'GemsOfWar_{lang}.json'
    url = f'{base_url}/{filename}.gz'
    r = requests.get(url)
    uncompressed = gzip.decompress(r.content)
    with open(filename, 'wb') as f:
        f.write(uncompressed)
