import datetime as dt
import scrapy
import json

from scrapy.http import HtmlResponse

from ..items import InstaTag, InstaPost, InstaUser, InstaFollow

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
    db_type= 'MONGO'
    login_url = 'https://www.instagram.com/accounts/login/ajax/'
    allowed_domains = ['www.instagram.com']
    start_urls = ['https://www.instagram.com/']
    api_url = '/graphql/query/'

    query_hash = {
        'tag_posts': "845e0309ad78bd16fc862c04ff9d8939",
        'foll': 'c76146de99bb02f6415203be841dd25a',
        'subs': 'd04b0a864b4b54837c0d870b0e77e076'
    }

    def __init__(self, login, password, tag_list, users_list,*args, **kwargs):
        self.login = login
        self.password = password
        self.tags = tag_list
        self.users = users_list
        super(InstagramSpider, self).__init__(*args, **kwargs)

    def parse(self, response):
        try:
            js_data = self.js_data_extract(response)
            yield scrapy.FormRequest(
                self.login_url,
                method='POST',
                callback=self.parse,
                formdata={
                    'username': self.login,
                    'enc_password': self.password,
                },
                headers={'X-CSRFToken': js_data['config']['csrf_token']}
            )
        except AttributeError as e:
            if response.json().get('authenticated'):
                for tag in self.tags:
                    yield response.follow(f'/explore/tags/{tag}/', callback=self.tag_parse)
                for user in self.users:
                    yield response.follow(f'/{user}', callback=self.user_parse)

    def tag_parse(self, response):
        tag = self.js_data_extract(response)['entry_data']['TagPage'][0]['graphql']['hashtag']

        yield InstaTag(
            date_parse=dt.datetime.utcnow(),
            index='tag',
            data={
                'id': tag['id'],
                'name': tag['name'],
                'profile_pic_url': tag['profile_pic_url'],
            }
        )
        yield from self.get_tag_posts(tag, response)

    def tag_api_parse(self, response):
        yield from self.get_tag_posts(response.json()['data']['hashtag'], response)

    def get_tag_posts(self, tag, response):
        if 'edge_hashtag_to_media' in tag.keys():
            if tag['edge_hashtag_to_media']['page_info']['has_next_page']:
                variables = {
                    'tag_name': tag['name'],
                    'first': 100,
                    'after': tag['edge_hashtag_to_media']['page_info']['end_cursor'],
                }
                url = f'{self.api_url}?query_hash={self.query_hash["tag_posts"]}&variables={json.dumps(variables)}'
                yield response.follow(
                    url,
                    callback=self.tag_api_parse,
                )

            yield from self.get_post_item(tag['edge_hashtag_to_media']['edges'])

    @staticmethod
    def get_post_item(edges):
        for node in edges:
            yield InstaPost(
                date_parse=dt.datetime.utcnow(),
                data=node['node'],
                img=node['node']['thumbnail_resources'][4]['src']
            )

    @staticmethod
    def js_data_extract(response):
        script = response.xpath('//script[contains(text(), "window._sharedData =")]/text()').get()
        return json.loads(script.replace("window._sharedData =", '')[:-1])

    def user_parse(self, response):
        user_data = self.js_data_extract(response)['entry_data']['ProfilePage'][0]['graphql']['user']

        yield InstaUser(
            index='user_data',
            date_parse=dt.datetime.utcnow(),
            data=user_data
        )

        yield from self.get_f_s_user(user_data, response)

    def get_f_s_user(self, user_data, response):
        variables = {"id": user_data['id'], "first": 100}
        url_f = f'{self.api_url}?query_hash={self.query_hash["foll"]}&variables={json.dumps(variables)}'
        yield response.follow(url=url_f, callback=self.get_api_foll, meta=user_data)
        url_s = f'{self.api_url}?query_hash={self.query_hash["subs"]}&variables={json.dumps(variables)}'
        yield response.follow(url=url_s, callback=self.get_api_subs, meta=user_data)

    def get_api_subs(self, response):
        user_data = response.meta
        subs_data = response.json()['data']['user']['edge_follow']
        yield from self.get_subscr_item(user_data, subs_data['edges'])
        if subs_data['page_info']['has_next_page']:
            variables = {
                "id": user_data['id'],
                "first": 100,
                "after": subs_data['page_info']['end_cursor'],
                         }
            url = f'{self.api_url}?query_hash={self.query_hash["subs"]}&variables={json.dumps(variables)}'
            yield response.follow(url=url, callback=self.get_api_subs, meta=user_data)

    def get_api_foll(self, response):
        user_data = response.meta
        foll_data = response.json()['data']['user']['edge_followed_by']

        yield from self.get_follow_item(user_data, foll_data['edges'])

        if foll_data['page_info']['has_next_page']:
            variables = {"id": user_data['id'],
                         "first": 100,
                         'after': foll_data['page_info']['end_cursor'],
                         }
            url = f'{self.api_url}?query_hash={self.query_hash["foll"]}&variables={json.dumps(variables)}'
            yield response.follow(url=url, callback=self.get_api_foll, meta=user_data)


    def get_follow_item(self, user_data, follow_user_data):
        for user in  follow_user_data:
            yield InstaFollow(
                date_parse=dt.datetime.utcnow(),
                user_id=user_data['id'],
                user_name=user_data['username'],
                follow_id=user['node']['id'],
                follow_name=user['node']['username'],

            )

    def get_subscr_item(self, user_data, subscr_user_data):
        for user in subscr_user_data:
            yield InstaFollow(
                date_parse=dt.datetime.utcnow(),
                user_id=user['node']['id'],
                user_name=user['node']['username'],
                follow_id=user_data['id'],
                follow_name=user_data['username'],
            )