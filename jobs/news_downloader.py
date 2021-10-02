import datetime
import html
import json
import os
import re
import time
from io import BytesIO

import feedparser
import html2markdown
import requests
from PIL import Image
from bs4 import BeautifulSoup

from base_bot import log


class NewsDownloader:
    LAST_POST_DATE_FILENAME = 'jobs/latest_known_post.dat'
    NEWS_FILENAME = 'jobs/posts.json'
    GOW_FEED_URL = 'https://gemsofwar.com/feed/'

    def __init__(self):
        self.last_post_date = datetime.datetime.min
        self.get_last_post_date()

    @staticmethod
    def is_banner(source):
        request = requests.get(source)
        image = Image.open(BytesIO(request.content))
        size = image.size
        ratio = size[0] / size[1]
        arbitrary_ratio_limit_for_banners = 5
        log.debug(f'[NEWS] Found a ration of {ratio} in {source}.')
        return ratio >= arbitrary_ratio_limit_for_banners

    def remove_tags(self, text):
        soup = BeautifulSoup(text, 'html5lib')
        source_images = soup.findAll('img')
        images = []
        for i in source_images:
            source = i['src']
            if not self.is_banner(source):
                images.append(source)

        forbidden_tags = re.compile(r'</?(a|img|div|figure).*?>')
        tags_removed = re.sub(forbidden_tags, '', text) \
            .replace('\n', '') \
            .replace('</em>', '</em> ')
        return images, html.unescape(html2markdown.convert(tags_removed))

    def reformat_html_summary(self, e):
        content = e['content'][0]['value']
        images, tags_removed = self.remove_tags(content)
        return images, tags_removed.strip()

    def get_last_post_date(self):
        if os.path.exists(self.LAST_POST_DATE_FILENAME):
            with open(self.LAST_POST_DATE_FILENAME) as f:
                self.last_post_date = datetime.datetime.fromisoformat(f.read().strip())

    def process_news_feed(self):
        url = f'{self.GOW_FEED_URL}?{int(time.time())}'
        feed = feedparser.parse(url)
        new_last_post_date = self.last_post_date

        posts = []
        for entry in feed['entries']:
            platform = 'switch' if 'Nintendo Switch' in entry.title else 'pc'

            posted_date = datetime.datetime.fromtimestamp(time.mktime(entry.published_parsed))
            if posted_date <= self.last_post_date:
                continue

            images, content = self.reformat_html_summary(entry)
            posts.append({
                'author': entry.author,
                'title': entry.title,
                'url': entry.link,
                'content': content,
                'images': images,
                'platform': platform,
            })
            new_last_post_date = max(new_last_post_date, posted_date)

        if posts:
            with open('jobs/posts.json', 'w') as f:
                json.dump(posts, f, indent=2)

            with open(self.LAST_POST_DATE_FILENAME, 'w') as f:
                f.write(new_last_post_date.isoformat())
