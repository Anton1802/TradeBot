from aiohttp import ClientSession
from bs4 import BeautifulSoup
import asyncio

class CSTrade():
    def __init__(self) -> None:
        self.__url_app = ""
        self.__url_api = ""
        self.__cookies = {}
        self.__balance = 0
        self.items = []

    def set_config(self, url_app: str, url_api: str, cookies: dict):
        self.__url_app = url_app
        self.__url_api = url_api
        self.__cookies = cookies

    async def get_balance(self) -> None:
        async with ClientSession(cookies=self.cookies) as session:
            async with session.get(self.url_app) as response:
                if response.status != 200:
                    raise Exception("Code 200")
                
                response_text = await response.text()
                
                soup = BeautifulSoup(response_text, 'lxml')
                balance_el = soup.find("span", attrs={"class": "balance-value balance-value-color"})
                
                self.__balance = float(balance_el.text)

    async def get_items(self) -> None:
        async with ClientSession() as session:
            async with session.get(self.__url_api) as response:
                if response.status != 200:
                    raise Exception("Code 200")
                
                response_json = await response.json(content_type="text/html")

                self.items = response_json['inventory']
