import asyncio
from aiohttp import ClientSession

class Tablevv:
    def __init__(self) -> None:
        self.__headers = None
        self.__cookies = None
        self.__page = 0
        self.items = []
        self.__filters = None
        self.__url = None
    
    def set_config(self, filters: dict, cookies: dict, url: str):
        self.__headers = {
            'Content-type': 'application/json; charset=utf-8',
            'Content-encoding': 'br',
        }
        self.__filters = filters
        self.__cookies = cookies
        self.__url = url

    async def get_items(self) -> list | None:
        async with ClientSession(cookies=self.__cookies) as session:
            while True:
                async with session.post(f"{self.__url}?page={self.__page}", json=self.__filters, headers=self.__headers) as response:
                    if response.status != 200:
                        raise Exception("Code 200")

                    response_json = await response.json() 

                    self.__page += 1

                    if len(response_json['items']) == 0:
                        break

                    for item in response_json['items']:
                        self.items.append(item)
  
        self.__page = 0

        return self.items
