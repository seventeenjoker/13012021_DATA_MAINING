# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import os
from dotenv import load_dotenv
import pymongo
from scrapy import Request
from scrapy.pipelines.images import ImagesPipeline


class GbParsePipeline:
    pass


class SaveToMongo:
    def __init__(self):
        client = pymongo.MongoClient()
        self.db = client["gb_parse_13012021"]

    def process_item(self, item, spider):
        self.db[spider.name].insert_one(item)
        return item


class GbImagePipeline(ImagesPipeline):
    def get_media_requests(self, item, info):
        yield Request(item._values['data']['display_url'])

    def item_completed(self, results, item, info):
        if results:
            item['img'] = [itm[1] for itm in results]
        return item
