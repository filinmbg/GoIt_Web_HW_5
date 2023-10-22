import aiohttp
import aiofiles
import asyncio
import logging
import names
import websockets
from datetime import datetime, timedelta
from websockets import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosedOK

logging.basicConfig(level=logging.INFO)


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
                    raise HttpError(f"Error status: {resp.statuAs} for {url}")
        except aiohttp.ClientConnectorError as err:
            raise HttpError(f'Connection error: {url}', str(err))


async def get_exchange():
    response = await request(f"https://api.privatbank.ua/p24api/exchange_rates?date=01.12.2014")
    return str(response)


async def get_exchange_for_date(date: str):
    response = await request(f"https://api.privatbank.ua/p24api/exchange_rates?date={date}")
    data = response.get('exchangeRate', [])
    exchange_rates = {}
    for item in data:
        if item['currency'] == 'USD':
            exchange_rates['USD'] = {
                'buyRate': item['purchaseRate'],
                'sellRate': item['saleRate']
            }
        elif item['currency'] == 'EUR':
            exchange_rates['EUR'] = {
                'buyRate': item['purchaseRate'],
                'sellRate': item['saleRate']
            }
    return exchange_rates


async def get_exchange_history(days: int):
    today = datetime.now()
    history = []
    for i in range(days):
        date = today - timedelta(days=i)
        date_str = date.strftime("%d.%m.%Y")
        exchange_data = await get_exchange_for_date(date_str)
        history.append(f"Exchange rate for {date_str}:\n USD to UAH - Buy: {exchange_data.get('USD', {}).get('buyRate', 'N/A')}, Sell: {exchange_data.get('USD', {}).get('sellRate', 'N/A')}\n EUR to UAH - Buy: {exchange_data.get('EUR', {}).get('buyRate', 'N/A')}, Sell: {exchange_data.get('EUR', {}).get('sellRate', 'N/A')}\n")
    return "\n".join(history)


async def handle_exchange_command(ws: WebSocketServerProtocol, args: str):
    if args.isdigit():
        days = int(args)
        if days > 0:
            exchange_history = await get_exchange_history(days)
            await ws.send(exchange_history)
        else:
            await ws.send("Please provide a positive number of days for exchange history.")
    else:
        await ws.send("Invalid argument. Please provide a positive number of days for exchange history.")


async def save_log(log_message):
    timestamp = str(datetime.now())
    log_line = f"{timestamp}: {log_message}"
    async with aiofiles.open("exchange_history.log", 'a') as log_file:
        await log_file.write(log_line + '\n')


class Server:
    clients = set()

    async def register(self, ws: WebSocketServerProtocol):
        ws.name = names.get_full_name()
        self.clients.add(ws)
        logging.info(f'{ws.remote_address} connects')

    async def unregister(self, ws: WebSocketServerProtocol):
        self.clients.remove(ws)
        logging.info(f'{ws.remote_address} disconnects')

    async def send_to_clients(self, message: str):
        if self.clients:
            [await client.send(message) for client in self.clients]

    async def ws_handler(self, ws: WebSocketServerProtocol):
        await self.register(ws)
        try:
            await self.distribute(ws)
        except ConnectionClosedOK:
            pass
        finally:
            await self.unregister(ws)

    async def distribute(self, ws: WebSocketServerProtocol):
        async for message in ws:
            if message.startswith('exchange'):
                command_parts = message.split()
                if len(command_parts) > 1:
                    command, args = command_parts[0], command_parts[1]
                    if command == 'exchange':
                        await save_log(f"{ws.name}: {message}")
                        await handle_exchange_command(ws, args)

                    else:
                        await self.send_to_clients(f"{ws.name}: {message}")
                else:
                    await self.send_to_clients(f"{ws.name}: {message}")
            else:
                await save_log(f"{ws.name}: {message}")
                await self.send_to_clients(f"{ws.name}: {message}")


async def main():
    server = Server()
    async with websockets.serve(server.ws_handler, 'localhost', 8080):
        await asyncio.Future()  # run forever

if __name__ == '__main__':
    asyncio.run(main())