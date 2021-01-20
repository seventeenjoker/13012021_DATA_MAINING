import json
import time
from pathlib import Path
import requests

from settings import CATEGORY_API

"""
Задача организовать сбор данных,
необходимо иметь метод сохранения данных в .json файлы
результат: Данные скачиваются с источника, при вызове метода/функции сохранения в файл скачанные данные сохраняются 
в Json файлы, для каждой категории товаров должен быть создан отдельный файл и содержать товары 
исключительно соответсвующие данной категории.

пример структуры данных для файла:

{
"name": "имя категории",
"code": "Код соответсвующий категории (используется в запросах)",
"products": [{PRODUCT},  {PRODUCT}........] # список словарей товаров соответсвующих данной категории
}

"""


class ParseError(Exception):
    def __init__(self, text):
        self.text = text


class Parse5ka:
    _headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/87.0.4280.141 Safari/537.36",
    }
    _params = {
        "records_per_page": 50,
    }

    def __init__(self, start_url: str, result_path: Path):
        self.start_url = start_url
        self.result_path = result_path

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

    def run(self):
        data = self.get_categories()
        for category in data:
            new_dict = {}
            file_path = self.result_path.joinpath(f'{category["parent_group_code"]}.json')
            new_dict["name"], new_dict["code"] = category["parent_group_name"], category["parent_group_code"]
            self._params['categories'] = category["parent_group_code"]
            new_dict["products"] = [product for product in self.parse(self.start_url)]
            self.save(new_dict, file_path)

    def parse(self, url: str) -> dict:
        while url:
            response = self.__get_response(
                url, params=self._params, headers=self._headers
            )
            data = response.json()
            url = data["next"]
            for product in data["results"]:
                yield product

    @staticmethod
    def save(data: dict, file_path: Path):
        with file_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False)

    def get_categories(self):
        response = self.__get_response(CATEGORY_API, params=self._params, headers=self._headers)
        return response.json()


if __name__ == "__main__":
    url = "https://5ka.ru/api/v2/special_offers/"
    result_path = Path(__file__).parent.joinpath("products")
    parser = Parse5ka(url, result_path)
    parser.run()
