# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import os
from dotenv import load_dotenv
from pymongo import MongoClient


class GbParsePipeline:
    def __init__(self):
        load_dotenv("../.env")
        data_base_url = os.getenv("DATA_BASE_URL")
        self.mongobase = MongoClient(data_base_url)["gb_parse_13012021"]

    def process_item(self, item, spider):
        if item.get('vac_name'):
            collection_name = 'vacancies'
        elif item.get('a_vac_name'):
            collection_name = 'employers_vacancies'
        else:
            collection_name = 'employers'
        collection = self.mongobase[spider.name][collection_name]
        collection.insert_one(item)
        return item
