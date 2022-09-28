from ast import For
import asyncio
import json
import aiohttp
import aiohttp_cors
import base64
import datetime
import logging
import requests
import traceback

from aiohttp import web
from aiohttp.web_runner import GracefulExit
from aiohttp_session import setup, get_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet
from typing import Awaitable, Callable

import helpers

from reverse_proxy import ReverseProxyRouter, ForwardResolver

logger = logging.getLogger('server')
logger.info("Aiohttp Server log")
logger.setLevel(logging.DEBUG)
tail: helpers.TailLogger = helpers.TailLogger(100)
log_handler = tail.log_handler
log_handler.setFormatter(helpers.GetLogFormatter())
logger.addHandler(log_handler)
logger.addHandler(helpers.GetConsoleLogHandler())


helpers.DebugTriggers.FunctionPrinting = True
helpers.DebugTriggers.Timing = False


@helpers.decorate_all_methods(helpers.exception_decorator, logger)
@helpers.decorate_all_methods(helpers.debug_decorator)
class WebClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.url = f"http://{self.host}:{self.port}"

    async def new_session(self):
        return aiohttp.ClientSession()
    
    async def get_response(self, path='/', url=None, params=None):
        if not url:
            url = self.url
        async with await self.new_session() as session:
            return await session.get(f"{url}{path}", params=params)
    
    async def put_response(self, path='/', url=None, data=""):
        if not url:
            url = self.url
        async with await self.new_session() as session:
            return await session.put(f"{url}{path}", data=json.dumps(data))

    async def post_response(self, path='/', url=None, data=""):
        if not url:
            url = self.url
        async with await self.new_session() as session:
                return await session.post(f"{url}{path}", data=json.dumps(data))

    async def print_response(self, resp: aiohttp.ClientResponse):
        if resp.status != requests.codes.ok:
            print(f"Response error: {await resp.text()} from {resp.request_info.method} {resp.request_info.url}")
        else:
            print(f"Response text: {await resp.text()}")
    
    async def send_check(self, params={}):
        async with await self.get_response("/check", params=params) as resp:
            await self.print_response(resp)

    async def send_put(self, data=""):
        async with await self.put_response("/data", data=data) as resp:
            await self.print_response(resp)

    async def send_command(self, name="", args=[], kwargs={}):
        async with await self.post_response("/command", data={"name": name, "args": args, "kwargs": kwargs}) as resp:
            await self.print_response(resp)


class Forwarder:
    app = None
    _instance = None
    routes = web.RouteTableDef()
    forwarding_url = None
    forwarding_port = None

    def __init__(self, url, port):
        self.url = url
        self.port = port

    def build(base_url, base_port, forwarding_url, forwarding_port):
        Forwarder._instance = Forwarder(base_url, base_port)
        Forwarder.forwarding_url = forwarding_url
        Forwarder.forwarding_port = forwarding_port
        return Forwarder._instance

    @routes.put('/{tail:.*}')
    @routes.post('/{tail:.*}')
    @routes.get('/{tail:.*}')
    async def forward_all(request: web.Request):
        """
        Responds with the correct url to use

        Args:
            request (web.Request): _description_

        Returns:
            _type_: _description_
        """
        location = f"{request.url.scheme}://{Forwarder.forwarding_url}:{Forwarder.forwarding_port}"
        print(f"Forwarding: {request.url} to {location}")
        return web.Response(status=requests.codes.misdirected_request, text=f"{location}", headers={"useUrl": location})

    @routes.get("/shutdown")
    async def shutdown(request):
        """
        Shuts the engine down

        Args:
            request (web.Request): the original request

        Raises:
            GracefulExit: _description_
        """
        print("Shutting down now")
        raise GracefulExit()

    @web.middleware
    async def middleware(request: web.Request, handler: Callable[[web.Request], Awaitable[web.Response]]):
        """
        This function is basically a decorator but for server functions

        Args:
            request (web.Request): _description_
            handler (Callable[[web.Request], Awaitable[web.Response]]): _description_

        Returns:
            web.Response: Response containing the response from the handled function (or an error)
        """
        try:
            resp = await handler(request)
            print(f"Resp {resp.text}")
            return resp
        except Exception as server_exception:
            msg = f"Server error for {request.method} {request.url}: {server_exception}: {traceback.format_exc()}"
            print(msg)
            return aiohttp.ClientResponseError(request_info=aiohttp.RequestInfo(request.url, method=request.method, headers=request.headers),
                                                   status=requests.codes.server_error, message=msg, headers=request.headers, history=())

    async def run_server(self, forever=True, timeout=0):
        Forwarder.app = web.Application(logger=logger, middlewares=[Forwarder.middleware])
        Forwarder.app.add_routes(Forwarder.routes)
        runner = web.AppRunner(Forwarder.app)
        await runner.setup()
        Forwarder.site = web.TCPSite(runner, self.url, self.port)
        await Forwarder.site.start()
        print(f"Running async web server at {Forwarder.site.name}")
        while forever:
            await asyncio.sleep(1)
        while timeout:
            await asyncio.sleep(1)
            timeout -=1

    async def run_demo(self):
        loop = asyncio.get_event_loop()
        fs = loop.create_task(self.run_server(forever=False, timeout=10))
        await asyncio.sleep(30)

if __name__ == "__main__":
    f = Forwarder.build("127.0.0.1", 12345, helpers.resolve_ip(), 12345)
    # asyncio.run(f.run_server(forever=False, timeout=10))
    asyncio.run(f.run_demo())