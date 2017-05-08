#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json  # to scrape Google ajax responses
import lxml.cssselect  # to fetch data from HTML by means of CSS selectors
import lxml.html  # to fetch data from HTML by means of CSS selectors
import os  # to operate with files and directories
import random  # to randomly select User-Agent header value
import requests  # to perform specific HTTP requests
import shutil  # to perform file downloading
import sys  # to get command line arguments
import urllib.parse # to quote URL parameters


class GoogleImagesCollector(object):
    # set of image urls - failed to download
    bad_urls = None
    # str for console logging actions
    BASE_LOG_LINE = None
    # base for ajax Google requests
    BASE_URL = \
        'https://www.google.com.ua/search?async=_id:rg_s,_pms:qs&q={query}&start=0&asearch=ichunk&tbm=isch'
    # base for ajax Google requests with tbs parameter
    BASE_TBS_URL = \
        'https://www.google.com.ua/search?async=_id:rg_s,_pms:qs&q={query}&start=0&asearch=ichunk&tbm=isch&tbs={tbs}'
    BASE_EXACT_URL = \
        'https://www.google.com.ua/search?async=_id:rg_s,_pms:qs&q="{query}"&start=0&asearch=ichunk&tbm=isch'
    BASE_EXACT_TBS_URL = \
        'https://www.google.com.ua/search?async=_id:rg_s,_pms:qs&q="{query}"&start=0&asearch=ichunk&tbm=isch&tbs={tbs}'

    # directory name to store images
    directory = None
    # set of image urls - successfully downloaded
    downloaded_urls = None
    # dict of allowed MIME types and corresponding file extensions
    MIME = {
        'image/gif': 'gif',
        'image/jpeg': 'jpg',
        'image/pjpeg': 'jpg',
        'image/png': 'png',
        'image/svg+xml': 'svg',
        'image/tiff': 'tiff',
        'image/vnd.microsoft.icon': 'ico',
        'image/vnd.wap.wbmp': 'wbmp',
        'image/webp': 'webp',
        }
    # search query
    query = None
    # requests session
    session = None
    # list of possible values of tbs parameter
    TBS = [
        'itp:photo',
        'itp:face',
        'itp:clipart',
        'itp:lineart',
        'qdr:d',
        'qdr:w',
        'itp:animated',
        'ic:color',
        'ic:gray',
        'ic:trans',
        ]

    def __init__(self, query, directory=None):
        """
        Initializes and object with a query and a directory name
        """
        self.query = query
        # if directory name is not provided, directory is named after the query
        self.directory = directory or os.path.join('images', query.replace('/', '&'))
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        self.BASE_LOG_LINE = query + ': {url}'
        self.session = requests.Session()

    def collect(self, imagenum=500):
        """
        Performs collecting of {imagenum} images
        into {self.directory} directory
        """
        if len(os.listdir(self.directory)) >= imagenum:
            print('{query}: there are already enough images.'.format(query=self.query))
            return
        query = encodeURIComponent(self.query)
        self.bad_urls = set()
        self.downloaded_urls = set()
        # the first url doesn't use tbs parameter
        page_urls = [GoogleImagesCollector.BASE_EXACT_URL.format(query=query)]
        # let's add urls with different possible values of tbs parameter
        page_urls.extend([GoogleImagesCollector.BASE_EXACT_TBS_URL.format(query=query,
                         tbs=tbs) for tbs in GoogleImagesCollector.TBS])
        # page_urls.append(GoogleImagesCollector.BASE_URL.format(query=query))
        # let's add urls with different possible values of tbs parameter
        # page_urls.extend([GoogleImagesCollector.BASE_TBS_URL.format(query=query,
        #                  tbs=tbs) for tbs in GoogleImagesCollector.TBS])
        # let's process urls until the job is done or there are no urls left
        for page_url in page_urls:
            print('\n')
            print(page_url)
            # let's fetch a page
            page = self.fetch_page(page_url)
            # let's process urls from this page
            for img_url in get_img_urls_from_page(page):
                if img_url not in self.downloaded_urls and img_url \
                    not in self.bad_urls:
                    # if the url is new
                    if self.download_image(img_url):
                        # and if the download is successful
                        # let's memoize the url as a good one
                        self.downloaded_urls.add(img_url)
                    else:
                        # if the download is not successful
                        # let's memoize the url as a bad one
                        self.bad_urls.add(img_url)

                if len(self.downloaded_urls) >= imagenum:
                    # if the job is done
                    print('{success} images downloaded.'.format(success=len(self.downloaded_urls)))
                    # let's finish
                    return
        # if we failed to fetch enough images
        print("I'm sorry! I've did my best: {imagenum} images.".format(imagenum=len(self.downloaded_urls)))

    def download_image(self, url, timeout=10):
        """
        Downloads an image by url
        """
        self.log(url)
        try:
            # let's request a file in stream mode
            response = self.session.get(url, stream=True,
                    timeout=timeout)
        except Exception:

            print('Download failed because of connection error.')
            return False
        if response.status_code == 200:
            try:
                # let's check if the file's MIME is allowed and
                # get a corresponding file extension
                file_extension = \
                    GoogleImagesCollector.MIME[response.headers['content-type'
                        ]]
            except KeyError:
                # if there is not any Content-Type or
                # if the MIME is disallowed
                print('Download was cancelled because something is wrong about data type.')
                return False
            file_path = os.path.join(self.directory, get_filename(url,
                    file_extension))

            try:
                # let's check if the file is already downloaded
                # by number of bytes
                if os.path.isfile(file_path) \
                    and os.stat(file_path).st_size \
                    == int(response.headers['content-length']):
                    print('This file is already present.')
                    return True
            except KeyError:
                # if Content-Length is not provided
                # we should try to download the file again
                pass
            # let's save the image
            with open(file_path, 'wb') as file:
                try:
                    response.raw.decode_content = True
                    shutil.copyfileobj(response.raw, file)
                except Exception:
                    print("Download was interrupted due to a connection error.")
                    return False
            return True
        else:
            # if the status code is not 200
            print('Download failed because of unknown reasons.')
            return False

    def fetch_page(self, url):
        """
        Fetches Google ajax page by url
        """
        return lxml.html.fromstring(json.loads(self.session.get(url,
                                    headers={'User-Agent': get_ua()}).content.decode('utf-8'
                                    ))[1][1])

    def log(self, url):
        """
        Logs an url
        """
        print(self.BASE_LOG_LINE.format(url=url))


def encodeURIComponent(input_str, quotate=urllib.parse.quote):
    """
    Python equivalent of javascript's encodeURIComponent
    """
    return quotate(input_str.encode('utf-8'), safe='~()*!.\'')


def get_filename(url, file_extension):
    """
    Transforms an url into a filename
    """
    # let's remove protocol name from url
    filename = url[url.index('//') + 2:]
    # is there an extension in this url?
    last_dot_index = filename.find('.', -5)
    filename = filename[:last_dot_index]
    # let's normalize the filename
    filename = slugify(filename)
    return '{filename}.{fileextension}'.format(filename=filename,
            fileextension=file_extension)


def get_img_url_from_meta(meta):
    """
    Returns image's url from a certain meta JSON
    """
    return json.loads(meta)['ou']


def get_img_urls_from_page(page,
                           META_SELECTOR=lxml.cssselect.CSSSelector('.rg_meta'
                           )):
    """
    Returns images' urls from a page
    """
    return [get_img_url_from_meta(meta_elem.text_content())
            for meta_elem in META_SELECTOR(page)]


def get_ua(ua_list=[
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36'
        ,
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36'
        ,
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/537.75.14'
        ,
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:29.0) Gecko/20100101 Firefox/29.0'
        ,
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.137 Safari/537.36'
        ,
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:28.0) Gecko/20100101 Firefox/28.0'
        ,
    ]):
    """
    Provides pseudo-random User-Agent from a saved list of ones
    """
    return random.choice(ua_list)


def slugify(value, keepcharacters=('_', )):
    """
    Removes non-alpha characters from text
    """
    return ''.join((c if c.isalnum() or c in keepcharacters else '_')
                   for c in value).rstrip()[:128]


if __name__ == '__main__':
    # if the module is being executed as a separate script
    if len(sys.argv) < 2:
        print('Provide some search query!')
    elif len(sys.argv) < 3:
        # if no imagenum is provided
        GoogleImagesCollector(sys.argv[1]).collect(imagenum=100)
    else:
        GoogleImagesCollector(sys.argv[1]).collect(imagenum=int(sys.argv[2]))
