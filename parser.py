import asyncio
from typing import Optional

import httpx
from bs4 import BeautifulSoup


class Parser:

    article = "https://ru.m.wikipedia.org/wiki/%D0%9A%D0%B0%D1%82%D0%B5%D0%B3%D0%BE%D1%80%D0%B8%D1%8F:%D0%90%D0%B2%D1%82%D0%BE%D0%BC%D0%BE%D0%B1%D0%B8%D0%BB%D0%B8_%D0%BF%D0%BE_%D0%BC%D0%B0%D1%80%D0%BA%D0%B0%D0%BC"
    domain = "https://ru.m.wikipedia.org/"

    @staticmethod
    async def get_page(url: str) -> bytes:
        """Получение контента страницы"""
        async with httpx.AsyncClient() as client:
            response = await client.get(url=url)
            assert response.status_code == 200

        return response.content

    @staticmethod
    def parse_page(page_content_to_bytes: bytes):
        return BeautifulSoup(page_content_to_bytes, 'html.parser')

    @staticmethod
    def prepare_brand_name(row_brand_name: str):
        brand_items = row_brand_name.split(" ")

        if len(brand_items) > 1:
            brand = brand_items[1]
        else:
            brand = row_brand_name

        return brand

    @staticmethod
    def prepare_model_name(brand, row_model_name) -> Optional[str]:
        # список запрещенных слов.
        incorrect_names = [
            "(автомобиль)", "ряд", "Шаблон",
            "автомобиля", "(автомобильная марка)", "автомобили", "автомобилей"
        ]

        name_items = row_model_name.split(" ")

        if len(name_items) == 1:
            name_items_with_other_del = row_model_name.split(":")

            if len(name_items_with_other_del) == 2:
                model = name_items_with_other_del[1] if name_items_with_other_del[0] not in incorrect_names else None
            else:
                model = row_model_name if row_model_name not in incorrect_names else None

        else:
            for index, item in enumerate(name_items):
                if len(item.split(":")) == 2:
                    return None

                if item in incorrect_names:
                    name_items.pop(index)

            model = " ".join(name_items)

        return model if model != brand else None

    async def collect(self):
        """Сбор данных"""
        collect_data = {}

        article_page_to_bytes = await self.get_page(self.article)
        parsed_article_page = self.parse_page(article_page_to_bytes)

        divBrandItems = parsed_article_page.findAll("div", class_="CategoryTreeItem")
        for divBrand in divBrandItems:
            tagA = divBrand.find('a')

            brand = self.prepare_brand_name(tagA.text)

            models_page_to_bytes = await self.get_page(f"{self.domain}{tagA.attrs['href']}")
            parsed_models_page = self.parse_page(models_page_to_bytes)

            divModelGroups = parsed_models_page.findAll("div", class_="mw-category-group")

            models = list()

            for divGroup in divModelGroups:
                tags_li = divGroup.findAll("li")

                for tag_li in tags_li:
                    model = self.prepare_model_name(brand, tag_li.next_element.text)
                    if model:
                        models.append(model)

            if len(divModelGroups) == 0:
                divContentBlocks = parsed_models_page.findAll("div", class_="mw-content-ltr")
                tags_li = divContentBlocks[-1].findAll("li")
                for tag_li in tags_li:
                    model = self.prepare_model_name(brand, tag_li.next_element.text)
                    if model:
                        models.append(model)

            collect_data[brand] = models

        with open("cars.json", "w") as file:
            file.write(str(collect_data))


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(Parser().collect())


