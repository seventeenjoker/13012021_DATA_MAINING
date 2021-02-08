import datetime
import scrapy
import json

from scrapy.http import HtmlResponse

from ..items import InstagramItem

"""
1) Задача авторизованным пользователем обойти список произвольных тегов +
2) Сохранить структуру Item олицетворяющую сам Tag (только информация о теге) +
3) Сохранить структуру данных поста, включая обход пагинации (каждый пост как отдельный item, словарь внутри node), вида:
    a) date_parse (datetime) время когда произошло создание структуры
    b) data - данные полученые от инстаграм
4) Скачать изображения всех постов и сохранить на диск
"""


class InstagramSpider(scrapy.Spider):
    name = 'instagram'
    allowed_domains = ['www.instagram.com']
    start_urls = ['https://www.instagram.com/']
    login_url = "https://www.instagram.com/accounts/login/ajax/"
    pag_url = "https://www.instagram.com/graphql/query/?query_hash=9b498c08113f1e09617a1703c22b2f32&variables="
    pag_dict = {"tag_name": "", "first": "", "after": ""}

    def __init__(self, login, password, *args, **kwargs):
        self.tags = ["python", "программирование", "developers"]
        self.login = login
        self.password = password
        super().__init__(*args, **kwargs)

    def parse(self, response: HtmlResponse):
        try:
            js_data = self.js_data_extractor(response)
            yield scrapy.FormRequest(
                self.login_url,
                method="POST",
                callback=self.parse,
                formdata={
                    "username": self.login,
                    "enc_password": self.password,
                },
                headers={
                    "X-CSRFToken": js_data['config']['csrf_token'],
                },
            )
        except AttributeError:
            if response.json().get('authenticated'):
                for tag in self.tags:
                    yield response.follow(f"/explore/tags/{tag}/", self.tag_parse)
                    # yield response.follow(f"/explore/tags/{tag}/", self.post_parse)

    def tag_parse(self, response: HtmlResponse):
        hashtag = self.js_data_extractor(response)['entry_data']['TagPage'][0]['graphql']['hashtag']
        data = {
            'name': hashtag['name'],
            'allow_following': hashtag['allow_following'],
            'profile_pic_url': hashtag['profile_pic_url'],
        }
        yield InstagramItem(date_parse=datetime.datetime.now(), data=data)
        yield from self.post_parse(hashtag, response)

    def post_parse(self, hashtag, response: HtmlResponse):
        if hashtag['edge_hashtag_to_media']['page_info']['has_next_page']:
            pag_dict = self.pag_dict
            pag_dict['tag_name'] = hashtag['name']
            pag_dict['first'] = '100'
            pag_dict['after'] = hashtag['edge_hashtag_to_media']['page_info']['end_cursor']
            pag_link = (self.pag_url + json.dumps(pag_dict)).replace(' ', '')
            yield response.follow(pag_link, callback=self.tag_api_parse)
        yield from self.get_post_item(hashtag["edge_hashtag_to_media"]["edges"])

    def tag_api_parse(self, response):
        yield from self.post_parse(response.json()["data"]["hashtag"], response)

    @staticmethod
    def get_post_item(edges):
        for node in edges:
            yield InstagramItem(date_parse=datetime.datetime.now(), data=node["node"])

    def js_data_extractor(self, response: HtmlResponse) -> dict:
        script = response.xpath('//body/script[contains(text(), "csrf_token")]/text()').get()
        return json.loads(script.replace("window._sharedData = ", "", 1)[:-1])
