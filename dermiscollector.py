#!/usr/bin/env python3

from googleimagescollector import GoogleImagesCollector
import lxml.cssselect # to fetch data from HTML by means of CSS selectors
import lxml.html # to fetch data from HTML by means of CSS selectors
import os # to check if the 'images' directory exists
# and to create it otherwise
import requests # to perform specific HTTP requests
import sys # to get command line arguments

# English alphabet
ALPHA = 'abcdefghijklmnopqrstuvwxyz'
# Urls' base
BASE_URL = 'http://www.dermis.net/dermisroot/en/list/{letter}/search.htm'
# Precompiled CSS selector for a diagnose
DIAGNOSE_SELECTOR = lxml.cssselect.CSSSelector(
    '#ctl00_Main_pnlSearchControl .list')


def collect_all_images(imagenum=5):
    """
    Downloads {imagenum} images for all the diagnoses
    """
    if not os.path.exists('images'):
        os.makedirs('images')
    # let's iterate over the alphabet
    for letter in ALPHA:
        page = lxml.html.fromstring(requests.get(BASE_URL.format(
            letter=letter)).content.decode('utf-8'))
        # let's get diagnoses' names from the page
        diagnoses = map(get_diagnose_from_elem, DIAGNOSE_SELECTOR(page))
        # let's iterate over the diagnoses from this page
        for diagnose in diagnoses:
            # and download images for them
            collect_images(diagnose, imagenum)
    print("All images were successfully collected.")


def collect_images(diagnose, imagenum=5):
    """
    Downloads {imagenum} images for a certain diagnose
    """
    GoogleImagesCollector(diagnose).collect(imagenum)


def get_diagnose_from_elem(diagnose_elem):
    """
    Returns the diagnose's name from a diagnose's DOM element
    """
    diagnose = diagnose_elem.text_content()
    try:
        return diagnose[:diagnose.index('(') - 1]
    except ValueError:
        return diagnose


if __name__ == '__main__':
    try:
        collect_all_images(imagenum=int(sys.argv[1]))
    except IndexError:
        # if there isn't imagenum provided
        collect_all_images()
