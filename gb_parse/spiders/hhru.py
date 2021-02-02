import scrapy
from scrapy.http import HtmlResponse
from gb_parse.loaders import HhruVacancyLoader, HhruCompanyLoader, HhruAVacancyLoader


class HhruSpider(scrapy.Spider):
    name = 'hhru'
    allowed_domains = ['hh.ru']
    start_urls = ['https://hh.ru/search/vacancy?schedule=remote&L_profession_id=0&area=113/']

    xpath_query = {
        'pagination': '//div[@data-qa="pager-block"]//a[@data-qa="pager-page"]',
        'vacancy': '//a[@data-qa="vacancy-serp__vacancy-title"]',
        'company': '//a[@data-qa="vacancy-serp__vacancy-employer"]',
        'company_vacancy': '//a[@data-qa="employer-page__employer-vacancies-link"]',
    }

    data_vac_xpath = {
        'vac_name': "//h1[@data-qa='vacancy-title']/text()",
        'salary': "//p[@class='vacancy-salary']/span/text()",
        'description': "//div[@class='vacancy-description']//text()",
        "key_tags": '//div[@class="bloko-tag-list"]//span[@data-qa="bloko-tag__text"]/text()',
        "company_url": '//a[@data-qa="vacancy-company-name"]/@href',
    }

    data_a_vac_xpath = {
        'a_vac_name': "//h1[@data-qa='vacancy-title']/text()",
        'salary': "//p[@class='vacancy-salary']/span/text()",
        'description': "//div[@class='vacancy-description']//text()",
        "key_tags": '//div[@class="bloko-tag-list"]//span[@data-qa="bloko-tag__text"]/text()',
        "company_url": '//a[@data-qa="vacancy-company-name"]/@href',
    }

    data_author_xpath = {
        'company_name': "//div[contains(@class, 'l-3')]//h1/span/text()",
        'company_web': '//a[contains(@data-qa, "company-site")]/@href',
        'company_scope': '//div[contains(@class, "employer-sidebar-content")]//p/text()',
        'company_description': '//div[contains(@data-qa, "company-description")]//text()',
    }

    @staticmethod
    def gen_task(response, link_list, callback):
        for link in link_list:
            yield response.follow(link.attrib["href"], callback=callback)

    def parse(self, response: HtmlResponse):
        pagination_links = response.xpath(self.xpath_query["pagination"])
        yield from self.gen_task(response, pagination_links, self.parse)
        vac_links = response.xpath(self.xpath_query["vacancy"])
        yield from self.gen_task(response, vac_links, self.vac_parse)
        company_links = response.xpath(self.xpath_query["company"])
        yield from self.gen_task(response, company_links, self.author_parse)

    def parse_next(self, response: HtmlResponse):
        pagination_links = response.xpath(self.xpath_query["pagination"])
        yield from self.gen_task(response, pagination_links, self.parse)
        author_vac_links = response.xpath(self.xpath_query["vacancy"])
        yield from self.gen_task(response, author_vac_links, self.a_vac_parse)

    def vac_parse(self, response:HtmlResponse):
        loader = HhruVacancyLoader(response=response)
        for key, selector in self.data_vac_xpath.items():
            loader.add_xpath(key, selector)
        loader.add_value('url', response.url)
        yield loader.load_item()

    def author_parse(self, response:HtmlResponse):
        loader = HhruCompanyLoader(response=response)
        for key, selector in self.data_author_xpath.items():
            loader.add_xpath(key, selector)
        loader.add_value('url', response.url)
        yield loader.load_item()
        if response.xpath(self.xpath_query['company_vacancy']).get():
            companys_vac = response.xpath(self.xpath_query["company_vacancy"])
            yield from self.gen_task(response, companys_vac, self.parse_next)

    def a_vac_parse(self, response:HtmlResponse):
        loader = HhruAVacancyLoader(response=response)
        for key, selector in self.data_a_vac_xpath.items():
            loader.add_xpath(key, selector)
        loader.add_value('url', response.url)
        yield loader.load_item()
