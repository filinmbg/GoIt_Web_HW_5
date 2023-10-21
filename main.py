import aiohttp
import argparse
import asyncio
import platform

import sys
from datetime import datetime, timedelta

CURRENCY = ['USD', 'EUR']
AVAILABLE_CURRENCIES = ['USD', 'EUR', 'CHF', 'GBP', 'PLZ', 'SEK', 'XAU', 'JPY', 'CAD', 'AUD']


class HttpError(Exception):
    pass


async def request(url: str):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result
                else:
                    raise HttpError(f"Error status: {resp.status} for {url}")
        except aiohttp.ClientConnectorError as err:
            raise "Не вийшло в мене дізнатись курс"


def parse_currency(exchange_rate, selected_currencies):
    date = exchange_rate['date']
    print(f'\n{date}:')
    for rate in exchange_rate['exchangeRate']:
        if rate['currency'] in selected_currencies:
            print(f'{rate["currency"]} sale: {rate["saleRate"]} purchase: {rate["purchaseRate"]}')


async def main(index_day, selected_currencies):
    d = datetime.now() - timedelta(days=int(index_day))
    shift = d.strftime('%d.%m.%Y')
    try:
        response = await request(f"https://api.privatbank.ua/p24api/exchange_rates?date={shift}")
        parse_currency(response, selected_currencies)

    except HttpError as err:
        print(err)


if __name__ == '__main__':
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    parser = argparse.ArgumentParser(description='Отримання курсу валют за певну кількість днів')
    parser.add_argument('days', type=int, help='Кількість днів для запиту (від 0 до 10)')
    parser.add_argument('--currencies', nargs='+', choices=AVAILABLE_CURRENCIES, default=CURRENCY, help='Вибрані валюти для відображення (розділені пробілами)') #--currencies USD EUR GBP

    args = parser.parse_args()

    # Перевірка на допустиму кількість днів (від 0 до 10)
    if 0 <= args.days <= 10:
        asyncio.run(main(args.days, args.currencies))
    else:
        print('Можна дізнатися курс валют не більше, ніж за останні 10 днів.')

