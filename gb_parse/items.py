# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class GbParseItem(scrapy.Item):
    pass


class AutoyoulaItem(scrapy.Item):
    _id = scrapy.Field()
    url = scrapy.Field()
    title = scrapy.Field()
    images = scrapy.Field()
    description = scrapy.Field()
    author = scrapy.Field()
    specifications = scrapy.Field()
    price = scrapy.Field()


class HhruVacancyItem(scrapy.Item):
    _id = scrapy.Field()
    url = scrapy.Field()
    vac_name = scrapy.Field()
    salary = scrapy.Field()
    description = scrapy.Field()
    key_tags = scrapy.Field()
    company_url = scrapy.Field()


class HHruCompanyItem(scrapy.Item):
    _id = scrapy.Field()
    url = scrapy.Field()
    company_name = scrapy.Field()
    company_web = scrapy.Field()
    company_scope = scrapy.Field()
    company_description = scrapy.Field()
