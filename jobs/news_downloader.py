import datetime
import json
import os
import re
import time

import feedparser
import html2markdown
from bs4 import BeautifulSoup


class NewsDownloader:
    LAST_POST_DATE_FILENAME = 'jobs/latest_known_post.dat'
    NEWS_FILENAME = 'jobs/posts.json'
    GOW_FEED_URL = 'https://gemsofwar.com/feed/'

    def __init__(self):
        self.last_post_date = datetime.datetime.min
        self.get_last_post_date()

    @staticmethod
    def remove_tags(text):
        soup = BeautifulSoup(text, 'html5lib')
        source_images = soup.findAll('img')
        images = []
        for i in source_images:
            source = i['src']
            if 'dividerline' not in source and 'ForumBanner' not in source:
                images.append(source)

        forbidden_tags = re.compile(r'</?(a|img|div).*?>')
        tags_removed = re.sub(forbidden_tags, '', text) \
            .replace('\n', '') \
            .replace('</em>', '</em> ')
        return images, html2markdown.convert(tags_removed).replace('&amp;', '&')

    @staticmethod
    def reformat_html_summary(e):
        content = e['content'][0]['value']
        images, tags_removed = NewsDownloader.remove_tags(content)
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
            is_nintendo = 'Nintendo Switch' in entry.title
            is_pc = not is_nintendo

            posted_date = datetime.datetime.fromtimestamp(time.mktime(entry.published_parsed))
            if posted_date <= self.last_post_date:
                continue

            if is_pc:
                images, content = self.reformat_html_summary(entry)
                posts.append({
                    'author': entry.author,
                    'title': entry.title,
                    'url': entry.link,
                    'content': content,
                    'images': images,
                })
            new_last_post_date = max(new_last_post_date, posted_date)

        if posts:
            with open('jobs/posts.json', 'w') as f:
                json.dump(posts, f, indent=2)

            with open(self.LAST_POST_DATE_FILENAME, 'w') as f:
                f.write(new_last_post_date.isoformat())
