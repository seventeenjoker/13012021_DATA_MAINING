import bs4
import database
import datetime
import requests
import time
import os

from dotenv import load_dotenv
from urllib.parse import urljoin


"""
Источник https://geekbrains.ru/posts/
Необходимо обойти все записи в блоге и извлеч из них информацию следующих полей:

+url страницы материала
+Заголовок материала
+Первое изображение материала (Ссылка)
+Дата публикации (в формате datetime)
+имя автора материала
+ссылка на страницу автора материала
комментарии в виде (автор комментария и текст комментария)
список тегов
реализовать SQL структуру хранения данных c следующими таблицами

Post
Comment
Writer
Tag
Организовать реляционные связи между таблицами

При сборе данных учесть, что полученый из данных автор уже может быть в БД и значит необходимо это заблаговременно проверить.
Не забываем закрывать сессию по завершению работы с ней
"""

class ParseError(Exception):
    def __init__(self, text):
        self.text = text


class GbParse:
    def __init__(self, start_url, db):
        self.db = db
        self.start_url = start_url
        self.done_url = set()
        self.tasks = [self.parse_task(self.start_url, self.pag_parse)]
        self.done_url.add(self.start_url)

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

    def _get_soup(self, *args, **kwargs):
        response = self._get_response(*args, **kwargs)
        soup = bs4.BeautifulSoup(response.text, 'lxml')
        return soup

    def get_datetime(self, soup):
        format = "%Y-%m-%dT%H:%M:%S"
        f_data = soup.find('div', attrs={'class': 'blogpost-date-views'}).time['datetime'].split('+')[0]
        return datetime.datetime.strptime(f_data, format)

    def get_comments(self, soup):
        url_id = soup.find('div', attrs={'class': 'm-t-xl'}).comments['commentable-id']
        param = {
            'commentable_type': 'Post',
            'commentable_id': int(url_id),
            'order': 'desc'
        }
        comments = requests.get('https://geekbrains.ru/api/v2/comments', param).json()
        comments_list = []

        def g_c(comment):
            for i in comment:
                name = i['comment']['user']['full_name']
                text = i['comment']['body']
                comments_list.append([name, text])
                if i['comment']['children'] != []:
                    g_c(i['comment']['children'])
        g_c(comments)
        return comments_list

    def run(self):
        for task in self.tasks:
            result = task()
            if result:
                self.save(result)

    def pag_parse(self, url, soup):
       self.create_parse_tasks(
           url, soup.find('ul', attrs={"class": "gb__pagination"}).find_all('a'), self.pag_parse
       )
       self.create_parse_tasks(
           url, soup.find('div', attrs={"class": "post-items-wrapper"}).find_all('a', attrs={"class": "post-item__title"}),
           self.post_parse
       )

    def create_parse_tasks(self, url, tag_list, callback):
        for a_tag in tag_list:
            a_url = urljoin(url, a_tag.get("href"))
            if a_url not in self.done_url:
                task = self.parse_task(a_url, callback)
                self.tasks.append(task)
                self.done_url.add(a_url)

    def get_img_url(self, soup):
        try:
            return soup.find('div', attrs={"class": "blogpost-content"}).find('img').get('src')
        except AttributeError:
            return None

    def post_parse(self, url, soup) -> dict:
        post_data = {
            'title': soup.find('h1', attrs={"class": "blogpost-title"}).text,
            'url': url,
            'img_url': self.get_img_url(soup),
            'date_time': self.get_datetime(soup)
        }
        author_tag_name = soup.find('div', attrs={"itemprop": "author"})
        author = {'name': author_tag_name.text,
                  'url': urljoin(url, author_tag_name.parent.get('href'))}
        tags_a = soup.find('article', attrs={"class": "blogpost__article-wrapper"}).find_all('a', attrs={'class': 'small'})
        tags = [{'url': urljoin(url, tag.get('href')), 'name': tag.text} for tag in tags_a]
        data = {
            'post_data': post_data,
            'author': author,
            'tags': tags,
            'comments': []
        }
        for comment in self.get_comments(soup):
            com_data = {
                'name': comment[0],
                'text': comment[1]
            }
            data['comments'].append(com_data)
        return data

    def parse_task(self, url, callback):
        def task():
            soup = self._get_soup(url)
            return callback(url, soup)
        return task

    def save(self, data):
        self.db.create_post(data)


if __name__ == "__main__":
    load_dotenv('.env')
    db = database.Database(os.getenv('SQL_DB_URL'))
    parser = GbParse("https://geekbrains.ru/posts", db)
    parser.run()
