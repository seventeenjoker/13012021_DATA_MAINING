import bs4
import pymongo
import os
import requests
import time

from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import urljoin

MONTHS = {
        'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
        'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
        'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12',
    }

"""
Необходимо собрать структуры товаров по акции и сохранить их в MongoDB

пример структуры и типы обязательно хранить поля даты как объекты datetime
{
    "url": str,
    "promo_name": str,
    "product_name": str,
    "old_price": float,
    "new_price": float,
    "image_url": str,
    "date_from": "DATETIME",
    "date_to": "DATETIME",
}
"""

class ParseError(Exception):
    def __init__(self, text):
        self.text = text


class MagnitParser:
    def __init__(self, start_url, data_client):
        self.start_url = start_url
        self.data_client = data_client
        self.data_base = self.data_client["gb_parse_13012021"]

    @staticmethod
    def _get_response(url: str, *args, **kwargs) -> requests.Response:
        while True:
            try:
                response = requests.get(url, *args, **kwargs)
                if response.status_code > 399:
                    raise ParseError(response.status_code)
                time.sleep(0.1)
                return response
            except (requests.RequestException, ParseError):
                time.sleep(0.5)
                continue

    @staticmethod
    def _get_soup(response):
        return bs4.BeautifulSoup(response.text, 'lxml')

    def get_time(self, s: str) -> list:
        return [i.split()[1] + ' ' + i.split()[2].replace(i.split()[2], MONTHS[i.split()[2]]) + ' 2021' for i in s.strip
        ('\n').split('\n')]

    def run(self):
        for product in self.parse(self.start_url):
            self.save(product)
        pass

    def parse(self, url) -> dict:
        soup = self._get_soup(self._get_response(url))
        catalog_main = soup.find('div', attrs={'class': 'сatalogue__main'})
        for product_tag in catalog_main.find_all("a", attrs={'class': 'card-sale'}):
            yield self._get_product_data(product_tag)

    @property
    def data_teamplate(self):
        return {
            "url": lambda tag: urljoin(self.start_url, tag.attrs.get("href")),
            "promo_name": lambda tag: tag.find('div', attrs={'class': "card-sale__header"}).text,
            "product_name": lambda tag: tag.find('div', attrs={'class': "card-sale__title"}).text,
            "old_price": lambda tag: float(tag.find('div', attrs={'class': "label__price_old"}).text.strip('\n').
                                           replace('\n', '.')),
            "new_price": lambda tag: float(tag.find('div', attrs={'class': "label__price_new"}).text.strip('\n').
                                           replace('\n', '.')),
            "image_url": lambda tag: urljoin(self.start_url, tag.attrs.get("src")),
            "date_from": lambda tag: datetime.strptime((self.get_time(tag.find('div', attrs={'class': "card-sale__date"}
                                                                               ).text))[0], '%d %m %Y'),
            "date_to": lambda tag: datetime.strptime((self.get_time(tag.find('div', attrs={'class': "card-sale__date"}).
                                                                    text))[1], '%d %m %Y'),
        }

    def _get_product_data(self, product_tag: bs4.Tag) -> dict:
        data = {}
        for key, pattern in self.data_teamplate.items():
            try:
                data[key] = pattern(product_tag)
            except (AttributeError, ValueError):
                pass
        return data

    def save(self, data):
        collection = self.data_base['magnit']
        collection.insert_one(data)
        pass


if __name__ == "__main__":
    load_dotenv("../.env")
    data_base_url = os.getenv("DATA_BASE_URL")
    data_client = pymongo.MongoClient(data_base_url)
    url = "https://magnit.ru/promo/?geo=moskva"
    parser = MagnitParser(url, data_client)
    parser.run()
