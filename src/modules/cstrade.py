from aiohttp import ClientSession
from bs4 import BeautifulSoup
import asyncio
import json

class CSTrade():
    def __init__(self) -> None:
        self.__url_app = ""
        self.__url_api = ""
        self.__url_trade = ""
        self.__cookies = {}
        self.__balance = 0
        self.items = []
        self.buy_items = []

    def set_config(self, url_app: str, url_api: str, url_trade: str, cookies: dict):
        self.__url_app = url_app
        self.__url_api = url_api
        self.__url_trade = url_trade
        self.__cookies = cookies

    async def __get_balance(self) -> None:
        async with ClientSession(cookies=self.__cookies) as session:
            async with session.get(self.__url_app) as response:
                if response.status != 200:
                    raise Exception("Code 200")
                
                response_text = await response.text()
                
                soup = BeautifulSoup(response_text, 'lxml')
                balance_el = soup.find("span", attrs={"class": "balance-value balance-value-color"})
                
                self.__balance = float(balance_el.text)

    async def __get_items(self) -> None:
        async with ClientSession() as session:
            async with session.get(self.__url_api) as response:
                if response.status != 200:
                    raise Exception("Code 200")
                
                response_json = await response.json(content_type="text/html")

                self.items = response_json['inventory']

    async def make_trade(self, items: dict[dict]) -> None:
        await self.__get_balance()
        await self.__get_items()

        for item_a in self.items:
            for item_b in items:
                if (item_a['market_hash_name'] == item_b['n']
                    and item_a['reservable'] == True):
                    self.buy_items.append(item_a)

        async with ClientSession(cookies=self.__cookies) as session:
            async with session.post(
                url=self.__url_trade,
                data={
                    "bot": "virtual",
                    "bot_chosen_items": json.dumps(self.buy_items),
                    "tt": "r",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
            ) as response:
                print(await response.json())
                print(len(self.buy_items))
