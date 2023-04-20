"""
Job code for news downloading and converting
"""

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
    """
    News Module for downloading from gemsofwar.com homepage
    and converting it into Discord compatible embeds,
    that not just look nice, but also preview more information
    than Discord's own webpage review widget.
    """
    LAST_POST_DATE_FILENAME = 'jobs/latest_known_post.dat'
    POSTS_CONTENTS_FILENAME = 'jobs/posts.json'
    NEWS_FILENAME = 'jobs/posts.json'
    GOW_FEED_URL = 'https://gemsofwar.com/feed/'
    USER_AGENT = 'garyatrics.com Discord Bot'
    REQUEST_TIMEOUT = 10

    def __init__(self):
        self.last_post_date = datetime.datetime.min
        self.get_last_post_date()

    @classmethod
    def is_banner(cls, source: str) -> bool:
        """
        Determine whether a source path is a banner image, or a normal image
        :param source:
        :return:
        """
        request = requests.get(source, timeout=cls.REQUEST_TIMEOUT)
        image = Image.open(BytesIO(request.content))
        size = image.size
        ratio = size[0] / size[1]
        arbitrary_ratio_limit_for_banners = 5
        log.debug('[NEWS] Found a ratio of %s in %s.', ratio, source)
        return ratio >= arbitrary_ratio_limit_for_banners

    def remove_tags(self, text: str) -> [list[str], str]:
        """
        remove blacklisted html tags from a piece of text, while saving image urls
        :param text:
        :return: list of image urls and content text
        """
        soup = BeautifulSoup(text, 'html5lib')
        source_images = soup.findAll('img')
        images = []
        for i in source_images:
            source = i['src']
            if not self.is_banner(source):
                images.append(source)

        forbidden_tags = re.compile(r'</?(a|img|div|figure|em)[^>]*>')
        tags_removed = re.sub(forbidden_tags, '', text).replace('\n', '')
        return images, html.unescape(html2markdown.convert(tags_removed))

    def reformat_html_summary(self, entry: dict) -> [list[str], str]:
        """
        extract contents from a website's entry and return images and contents without html tags
        :param entry:
        :return:
        """
        content = entry['content'][0]['value']
        images, tags_removed = self.remove_tags(content)
        return images, tags_removed.strip()

    def get_last_post_date(self) -> None:
        """
        fetches the date of the last post being fetched
        :return: None
        """
        if os.path.exists(self.LAST_POST_DATE_FILENAME):
            with open(self.LAST_POST_DATE_FILENAME, encoding="utf-8") as date_file:
                self.last_post_date = datetime.datetime.fromisoformat(date_file.read().strip())

    def process_news_feed(self) -> None:
        """
        fetches the feed, goes through every entry and converts it into
        a Discord embed compatible format, then saving the JSON into
        the posts file.
        :return: None
        """
        url = f'{self.GOW_FEED_URL}?{int(time.time())}'
        try:
            response = requests.get(url, timeout=5)
            content = BytesIO(response.content)
        except requests.RequestException as e:
            log.warn(f'Could not fetch {url}: {e}')
            return

        feed = feedparser.parse(content)
        new_last_post_date = self.last_post_date

        posts = []
        for entry in feed['entries']:
            platform = 'switch' if 'switch' in entry.title.lower() else 'pc'

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
            with open(self.POSTS_CONTENTS_FILENAME, 'w', encoding="utf-8") as posts_file:
                json.dump(posts, posts_file, indent=2)

            with open(self.LAST_POST_DATE_FILENAME, 'w', encoding="utf-8") as date_file:
                date_file.write(new_last_post_date.isoformat())
