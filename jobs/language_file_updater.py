#!/usr/bin/env python3
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
    print(f'[DEBUG] Downloading language file {filename}.gz...')
    url = f'{base_url}/{filename}.gz'
    r = requests.get(url)
    print(f'[DEBUG] Decompressing into {filename}...')
    uncompressed = gzip.decompress(r.content)
    with open(filename, 'wb') as f:
        f.write(uncompressed)
