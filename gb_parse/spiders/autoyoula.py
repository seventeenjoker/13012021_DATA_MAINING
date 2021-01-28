import os
from urllib.parse import urljoin
import conv_url as prs
import pymongo
import re
import scrapy

from dotenv import load_dotenv
from scrapy.http import Response, HtmlResponse

"""
Обойти все марки авто и зайти на странички объявлений +
Собрать след стуркутру и сохранить в БД Монго +
Название объявления +
Список фото объявления (ссылки) +
Список характеристик +
Описание объявления +
ссылка на автора объявления +
дополнительно попробуйте вытащить телефон 
"""


class AutoyoulaSpider(scrapy.Spider):
    name = 'autoyoula'
    allowed_domains = ['auto.youla.ru']
    start_urls = ['https://auto.youla.ru/']
    css_query = {
        'brand': 'div.ColumnItemList_column__5gjdt a.blackLink',
        'pagination': 'div.Paginator_block__2XAPy a.Paginator_button__u1e7D',
        'ads': 'article.SerpSnippet_snippet__3O1t2 a.SerpSnippet_name__3F7Yu',

    }

    data_query = {
        'title': lambda resp: resp.css("div.AdvertCard_advertTitle__1S1Ak::text").get(),
        'price': lambda resp: float(resp.css('div.AdvertCard_price__3dDCr::text').get().replace("\u2009", '')),
        'images': lambda resp: resp.css('section.PhotoGallery_thumbnails__3-1Ob button::attr(style)').re('(https?://[^\s]+)\)'),
        'specifications': lambda resp: AutoyoulaSpider.specifications_parse(resp),
        'describe': lambda resp: resp.css("div.AdvertCard_descriptionWrap__17EU3 div.AdvertCard_descriptionInner__KnuRi::text").get(),
        'author': lambda resp: AutoyoulaSpider._parse_autor(resp),
    }

    def __init__(self):
        load_dotenv("../.env")
        data_base_url = os.getenv("DATA_BASE_URL")
        self.db = pymongo.MongoClient(data_base_url)['jula_collection']

    @staticmethod
    def gen_task(response, list_link, callback):
        for link in list_link:
            yield response.follow(link.attrib.get('href'), callback=callback)

    def get_specification(self, response):
        itm = response.css('.AdvertSpecs_label__2JHnS::text').get()
        return {itm.css('.AdvertSpecs_label__2JHnS::text').get(): itm.css('.AdvertSpecs_data__xK2Qx::text').get()
                    or itm.css('a::text').get() for itm in response.css('.AdvertSpecs_row__ljPcX')}

    def get_img(self, response):
        imgs = []
        for img in response.css('button.PhotoGallery_thumbnailItem__UmhLO'):
            imgs.append(img.attrib.get('style').split('(')[1][:-1])
        return imgs

    def parse(self, response):
        yield from self.gen_task(response, response.css(self.css_query['brand']), self.brand_parse)

    def brand_parse(self, response:Response):
        yield from self.gen_task(response, response.css(self.css_query['pagination']), self.brand_parse)
        yield from self.gen_task(response, response.css(self.css_query['ads']), self.ads_parse)

    @staticmethod
    def specifications_parse(response):
        data = {}
        for name, value in zip(response.css('div.AdvertCard_specs__2FEHc div.AdvertSpecs_label__2JHnS::text'),
                               response.css(
                                   'div.AdvertCard_specs__2FEHc div.AdvertSpecs_data__xK2Qx::text, div.AdvertCard_specs__2FEHc a::text')):
            data[name.get()] = value.get()
        return data

    def ads_parse(self, response:Response):
        data = {}
        for name, query in self.data_query.items():
            try:
                data[name] = query(response)
            except (ValueError, AttributeError):
                continue
        if self.db is not None:
            self._save(data)

    def _save(self, data):
        collection = self.db['jula_cars']
        collection.insert_one(data)

    @staticmethod
    def _get_script_content(response:HtmlResponse)->dict:
        for resp_script in response.css("script"):
            find_content_script= re.search(r'(?<=<script>window.transitState = decodeURIComponent\(").*(?="\);</script>)', resp_script.get())
            if find_content_script == None:
                continue
            res = find_content_script.group(0)
            decoder_uri = prs.DecodeURIComponent(res)
            return decoder_uri.to_dict()

    @staticmethod
    def _parse_autor(response:HtmlResponse)->str:
        script_dict = AutoyoulaSpider._get_script_content(response)
        profile = script_dict['~#iM']['advertCard']['^0']['youlaProfile']
        if profile!=None:
            return urljoin(AutoyoulaSpider.user_url, 'user/{0}'.format(profile['^0']['youlaId']))
        else:
            return urljoin(AutoyoulaSpider.start_urls[0], script_dict['~#iM']['advertCard']['^0']['sellerLink'])
