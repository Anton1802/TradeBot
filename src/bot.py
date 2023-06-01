import json
import asyncio
import logging
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError

import aiogram.utils.markdown as md
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher.filters import Filter
from aiogram.utils import executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Text

from modules.tablevv import Tablevv
from modules.cstrade import CSTrade

class IsAdmin(Filter):
    async def check(self, message: types.Message):
        return message.from_user.id in get_config_gen()['admins']


class Form(StatesGroup):
    parameter = State()
    value = State()


def get_config_gen() -> object:
    config = None
    with open(Path('configs', 'gen_conf.json'), 'r') as file:
        config = json.load(file)

    return config

def get_config_temp() -> object:
    config = None
    with open(Path('configs', 'temp_conf.json'), 'r') as file:
        config = json.load(file)

    return config

def update_config_temp(data: object) -> None:
    with open(Path('configs', 'temp_conf.json'), 'w') as file:
        json.dump(data, file)

logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()
bot = Bot(token=get_config_gen()['token_bot'])
dp = Dispatcher(bot, storage=storage)

scheduler = AsyncIOScheduler() 

@dp.message_handler(IsAdmin(), state='*', commands='cancel')
async def cancel_state(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info('Cancelling state %r', current_state)

    await state.finish()

    await message.answer('Cancelled.', reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(IsAdmin(), commands=['start'])
async def start(message: types.Message):
    text = md.text(
        md.text(md.text("Hello, administrator "), md.bold("TradeBot")),
        md.text("To find out which commands are available\."),
        md.text(md.text("Please use a command"), md.code("/help")),
        sep="\n"
    )
    await message.answer(text, parse_mode='MarkdownV2')

@dp.message_handler(IsAdmin(), commands=['help'])
async def help(message: types.Message):
    text = md.text(
        md.text(md.bold("Commands bot: ")),
        md.text(md.code('/start'), md.text('\- запускает приветствие для админа')),
        md.text(md.code('/cancel'), md.text('\- отменяет машину состояний')),
        md.text(
            md.code('/config'), 
            md.text('\- админская функция, которая позволяет увидеть глобальные параметры')
        ),
        md.text(
            md.code('/set_config'),
            md.text('\- позволяет вручную установить параметр'),
        ),
        md.text(
            md.code('/cstrade_start_trade'),
            md.text('\- запускает трейдинг в боте'),
        ),
        md.text(
            md.code('/cstrade_stop_trade'),
            md.text('\- останавливает трейдинг в боте'),
        ),
        sep="\n",
    )
    await message.answer(text, parse_mode='MarkdownV2')

@dp.message_handler(IsAdmin(), commands=['config'])
async def config_view(message: types.Message):
    config = get_config_temp()
    string = ""
    string += f"{md.bold('Parameters: ')}\n"
    for name_parameter in config:
        string += f"{md.bold(name_parameter)}: {md.code(config[name_parameter])} \n"

    await message.answer(string, parse_mode='MarkdownV2')
    
@dp.message_handler(IsAdmin(), commands=['set_config'])
async def start_set_config(message: types.Message):
    await Form.parameter.set()

    await message.answer("Please enter name parameter: ")

@dp.message_handler(IsAdmin(), state=Form.parameter)
async def process_set_config_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['parameter_name'] = message.text

        config = get_config_temp()
        if config.get(data['parameter_name']) == None:
            await message.answer("The parameter does not exists")
        else:
            await Form.next()
            await message.answer("Please enter value parameter: ")

@dp.message_handler(IsAdmin(), state=Form.value)
async def process_set_config_value(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['parameter_value'] = message.text

        config = get_config_temp()
        config[data['parameter_name']] = data['parameter_value']

        update_config_temp(config)

        await message.answer(f"Parameter {data['parameter_name']} changed!")

    await state.finish()

@dp.message_handler(IsAdmin(), commands='cstrade_start_trade')
async def start_cstrade(message: types.Message):
    if(len(scheduler.get_jobs()) == 0):
        scheduler.add_job(
            process_cstrade,
            "interval",
            seconds=5,
            args=(message, ),
            id='process_cstrade'
        )
        await message.answer("Trade starting!")
        await message.answer("Please wait...")
    else:
        await message.answer("Trade is already started!")
    
async def process_cstrade(message: types.Message):
    config = get_config_temp()
    admins = get_config_gen()['admins']
    
    tablevv = Tablevv()
    tablevv.set_config(config['tablevv_filters'], config['tablevv_cookies'], config['tablevv_url'])

    cstrade = CSTrade()
    cstrade.set_config(
        config['cstrade_url_app'],
        config['cstrade_url_api_inventory'],
        config['cstrade_url_api_trade'], 
        config['cstrade_cookies'],
        config['cstrade_item_count_max'],
    )

    tablevv_items = await tablevv.get_items()
    
    buy_items = await cstrade.make_trade(tablevv_items)

    steam_url = "https://steamcommunity.com/market/listings"
    if buy_items is not None:
        for admin in admins:
            for item, t_item in zip(buy_items['cstrade_items'], buy_items['table_items']):
                await message.bot.send_message(
                    admin,
                    md.text(
                        md.text(
                            md.hbold("Link on item: "),
                            md.hlink('URL', f"{steam_url}/{item['app_id']}/{item['market_hash_name'].replace('+', ' ')}"),
                        ),
                        md.text(
                            md.hbold("Price 1 platform: "),
                            md.hcode(f"{t_item['i1']['p']}$"),
                        ),
                        md.text(
                            md.hbold("Price 2 platform: "),
                            md.hcode(f"{t_item['i2']['p']}$"),
                        ),
                        md.text(
                            md.hbold("Profit: "),
                            md.hcode(f"{t_item['p']}%")
                        ),
                        sep="\n",
                    ),
                    parse_mode="HTML",
                )

@dp.message_handler(IsAdmin(), commands='cstrade_stop_trade')
async def stop_cstrade(message: types.Message):
    try:
        scheduler.pause_job(job_id='process_cstrade')
        scheduler.remove_job(job_id='process_cstrade')
    except JobLookupError:
        await message.answer("Trading is not running!")
    else:
        await message.answer("Trading stopped!")

if __name__ == "__main__":
    scheduler.start()
    executor.start_polling(dp)
