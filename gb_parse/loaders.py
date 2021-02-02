import re
from urllib.parse import urljoin
from scrapy import Selector
from scrapy.loader import ItemLoader
from .items import AutoyoulaItem, HhruVacancyItem, HHruCompanyItem
from itemloaders.processors import TakeFirst, MapCompose, Join


def get_author_id(item):
    re_pattern = re.compile(r"youlaId%22%2C%22([a-zA-Z|\d]+)%22%2C%22avatar")
    result = re.findall(re_pattern, item)
    return result


def clear_unicode(itm):
    return itm.replace("\u2009", "").replace("\xa0", "")

def clear_str(itm):
    return itm.strip()

def get_specifications(item):
    tag = Selector(text=item)
    name = tag.xpath("//div[@class='AdvertSpecs_label__2JHnS']/text()").get()
    value = tag.xpath("//div[@class='AdvertSpecs_data__xK2Qx']//text()").get()
    return {name: value}

def flat_dict(items):
    result = {}
    for itm in items:
        result.update(itm)
    return result


class AutoyoulaLoader(ItemLoader):
    default_item_class = AutoyoulaItem
    url_out = TakeFirst()
    title_out = TakeFirst()
    price_in = MapCompose(clear_unicode, float)
    price_out = TakeFirst()
    author_in = MapCompose(get_author_id, lambda a_id: urljoin("https://youla.ru/user/", a_id))
    author_out = TakeFirst()
    description_out = TakeFirst()
    specifications_in = MapCompose(get_specifications)
    specifications_out = flat_dict

def vac_description(itm):
    if '.tmpl_hh_wrapper' in itm or 'window.jquery' in itm:
        itm = ''
        return itm
    else:
        return itm.replace("\u2009", "").replace("\xa0", "").replace('\n', "").replace('\u200b', "")

class HhruVacancyLoader(ItemLoader):
    default_item_class = HhruVacancyItem
    url_out = TakeFirst()
    vac_name_out = TakeFirst()
    salary_in = MapCompose(clear_unicode)
    salary_out = Join()
    description_in = MapCompose(vac_description)
    description_out = Join()
    key_tags_in = MapCompose(vac_description)
    key_tags_out = Join()
    company_url_in = MapCompose(lambda a_com: urljoin("https://hh.ru/", a_com))
    company_url_out = TakeFirst()

class HhruCompanyLoader(ItemLoader):
    default_item_class = HHruCompanyItem
    url_out = TakeFirst()
    company_name_in = MapCompose(clear_unicode)
    company_name_out = Join()
    company_web_out = TakeFirst()
    company_scope_out = Join()
    company_description_in = MapCompose(clear_unicode)
    company_description_out = Join()
