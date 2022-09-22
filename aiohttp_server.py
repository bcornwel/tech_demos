import aiohttp
import aiohttp_cors
import asyncio
import base64
import functools
#import jinja2  # for html templating but i don't think we have enough need for that.. yet...
import importlib
import inspect
import json
import logging
import os
import requests
import time
import traceback

from aiohttp import web
from aiohttp_session import setup, get_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from aiohttp_swagger import setup_swagger
from aiohttp.web_runner import GracefulExit
from cryptography import fernet
from datetime import datetime
from typing import Awaitable, Callable, Tuple

import helpers


logging.basicConfig(filename="aiohttp_server.log", level=logging.DEBUG)
logger = logging.getLogger('server')
logger.info("Aiohttp Server log")


helpers.DebugTriggers.FunctionPrinting = False
helpers.DebugTriggers.Timing = False
helpers.DebugTriggers.ReturnValues = False


class ServerSchemas:
    Command = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "pattern": helpers.Const.Regex.AlphaNumeric,
                "error message": f"Command name should match the format {helpers.Const.Regex.AlphaNumeric}"
            },
            "args": {
                "type": "array",
                "minItems": 0,
                "maxItems": 10
            },
            "kwargs": {
                "type": "object",
                "minItems": 0,
                "maxItems": 10
            }
        }
    }


def server_decorator(func: Callable) -> Callable:
    """
    prints the return value, meant for server functions to see what data is being returned

    Args:
        func (Callable): function to wrap

    Returns:
        Callable: wrapped function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        ret = func(*args, **kwargs)
        print(func.__name__, "returned", f"{ret}")
        return ret
    return wrapper


def client_decorator(func: Callable) -> Callable:
    """
    prints the return value, meant for server functions to see what data is being returned

    Args:
        func (Callable): function to wrap

    Returns:
        Callable: wrapped function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # for arg in args:
        #     arg = json.dumps(utils.remove_comments(arg))
        for arg in args:
            arg = json.dumps(arg)
        ret = func(*args, **kwargs)
        print(func.__name__, "returned", f"{ret}")
        return ret
    return wrapper


HandlerRegistry = dict()


#@helpers.decorate_all_methods(server_decorator)
@helpers.decorate_all_methods(helpers.debug_decorator)
class WebServer:
    routes = web.RouteTableDef()
    put_dict = dict()  # put is idempotent
    post_list = list()
    expected_put_params = ["message", "data"]
    pending_tasks = []
    _instance = None
    # dynamic_router = web.UrlDispatcher()
    running_tasks = []
    log_reload = 1000
    site = None

    def __init__(self):
        logger.setLevel(logging.DEBUG)
        self.tail: helpers.TailLogger = helpers.TailLogger(100)
        log_handler = self.tail.log_handler
        log_handler.setFormatter(helpers.GetLogFormatter())
        logger.addHandler(log_handler)
        logger.addHandler(helpers.GetConsoleLogHandler())
    
    def create():
        WebServer._instance = WebServer()
        return WebServer._instance

    @routes.get("/shutdown")
    async def shutdown(request):
        """
        Shuts the engine down

        Args:
            request (web.Request): the original request

        Raises:
            GracefulExit: _description_
        """
        logger.info("Shutting down now")
        raise GracefulExit()

    @routes.get("/favicon.ico")
    async def favicon(request):
        return web.FileResponse("")

    @routes.get("/docs")
    async def pdoc_files(request):
        """
        Serves up pdoc documentation

        Args:
            request (web.Request): the original request

        Returns:
            _type_: _description_
        """
        f = f"docs/html/{os.path.basename(__file__)[:-3]}.html"
        assert os.path.exists(f), f"Unable to find {f}"
        logger.debug(f"Serving up {f}")
        return web.FileResponse(path=f)

    @routes.get("/")
    async def handler(request):
        """
        session handler for keeping track of session info

        Args:
            request (web.Request): the original request

        Returns:
            _type_: _description_
        """
        session = await get_session(request)
        last_visit = session['last_visit'] if 'last_visit' in session else datetime.now()
        text = 'Last visited: {}'.format(last_visit)
        return web.Response(text=text)

    @routes.get("/update")
    async def update(request:web.Request):
        """
        Updates the api routes with a file
        TODO: need to do more safety checking

        Args:
            request (web.Request): the original request

        Returns:
            _type_: _description_
        """
        # from api_ww38 import routes as new_routes
        to_import:dict = request.query
        to_import = to_import.get("file", "api_ww38")
        if to_import.endswith(".py"):
            mod_name = to_import[:-3]
            path = to_import
        else:
            path = f"{to_import}.py"
            mod_name = to_import
        # WARNING!!! NEED TO DO A LOT OF VALIDATION HERE SINCE THIS DYNAMICALLY IMPORT/EXECUTES UNKNOWN CODE
        # SHOULD PROBABLY DO A HASH COMPARISON TO ENSURE IT'S OUR CODE
        spec = importlib.util.spec_from_file_location(mod_name, path)
        new_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(new_mod)
        new_routes = new_mod.routes
        added = WebServer.update_routes(new_routes)
        return web.Response(text=f"Updated with {added} routes")

    def update_routes(new_routes: web.RouteTableDef):
        """
        adds the new routes to the current router object, unfreezes the router

        Args:
            new_routes (web.RouteTableDef): the routing table

        Returns:
            _type_: _description_
        """
        WebServer.app.router._frozen = False
        routes_added = WebServer.app.router.add_routes(new_routes)
        WebServer.app.router._frozen = True
        return routes_added

    @routes.get("/ws")
    async def websocket_handler(request):
        """
        Handles websocket requests
        useful for command control similar to command line

        Args:
            request (web.Request): the original request

        Returns:
            _type_: _description_
        """
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == 'close':
                    await ws.close()
                else:
                    await ws.send_str(msg.data + '/answer')
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error('ws connection closed with exception %s' %
                    ws.exception())
        logger.info('websocket connection closed')
        return ws

    @routes.get("/redirect")
    async def redirect_handler(request):
        """
        Handles redirects to other sites

        Args:
            request (web.Request): the original request

        Returns:
            _type_: _description_
        """
        location = "https://github.com/bcornwel/tech_demos"
        return web.HTTPFound(location=location)

    @web.middleware
    async def middleware(request: web.Request, handler: Callable[[web.Request], Awaitable[web.Response]]):
        """
        This function is basically a decorator but for server functions

        Args:
            request (web.Request): _description_
            handler (Callable[[web.Request], Awaitable[web.Response]]): _description_

        Returns:
            _type_: _description_
        """
        try:
            resp = await handler(request)
            return resp
        except Exception as server_exception:
            msg = f"Server error for {request.method} {request.url}: {server_exception}: {traceback.format_exc()}"
            logger.error(msg)
            return aiohttp.ClientResponseError(request_info=aiohttp.RequestInfo(request.url, method=request.method, headers=request.headers()),
                                                   status=requests.codes.error, message=msg, headers=request.headers())
    
    @routes.get('/log')
    async def log_response(request):
        """
        Provides a log response

        Args:
            request (web.Request): the original request object

        Returns:
            web.Response: the response containing the html that displays the log data

        ---
        description: End-point for displaying logs, should be used in a browser, as this provides html/js which will auto-refresh the log display
        tags:
        - Logging
        responses:
            "200":
                description: successfully displayed logs
        """
        content = "<br/>".join(WebServer._instance.tail.contents().split("\n"))
        script = "<script>setTimeout(function(){window.location.reload();}, " + f"{WebServer.log_reload}" + ");" + \
                    'function scrollToBottom() { window.scrollTo(0, document.body.scrollHeight); } history.scrollRestoration = "manual"; window.onload = scrollToBottom;</script>'
        style = "<style>div { background: gray; overflow: hidden; } div form { float: right; margin-right:50px;} div h1 p { color: white; text-align: center; display: inline-block; width: 100%; margin-right: -50%; }</style>"
        head = f"<head><title>Log</title>{script}{style}</head>"
        shutdown_link = f"'{WebServer.site.name}/shutdown'"
        shutdown_button = f'<form action={shutdown_link}> <input type="submit" value="Shutdown engine" /></form>'
        body = f'<div><br/><p>{content}</p>{shutdown_button}<h1>Log data as of {datetime.now()}</h1></div>'
        text = head + body
        return web.Response(text=text, content_type='text/html')

    @routes.get('/check')  # custom path
    async def check_response(request:web.Request):
        """
        Basic get request used to demo getting info

        Args:
            request (web.Request): the original request

        Returns:
            _type_: _description_
        
        ---
        description: End-point for displaying demo put an/or post data
        tags:
        - GET
        - state checking
        responses:
            "200":
                description: successfully displayed put or post data
        """
        p = request.query.get("path", None)
        if p == "put":
            return await WebServer.check_put_response(request)
        elif p == "post":
            return await WebServer.check_post_response(request)
        else:
            return web.Response(text="Nothing to check")
        
    @routes.get('/check/put')  # custom multi-layer path
    async def check_put_response(request):
        return web.Response(text=f"Put contains {len(WebServer.put_dict)}")

    @routes.get('/check2/put')  # custom multi-layer path
    async def check2_put_response(request):
        return web.Response(text=f"Put contains {len(WebServer.put_dict)+1}")
    
    @routes.get('/check/post')
    async def check_post_response(request):
        return web.Response(text=f"Post contains {len(WebServer.post_list)}")

    @routes.put('/data')
    async def put_response(request: web.Request):
        data = await request.post()
        logger.debug(f"Putting data {data.keys()}")
        added = 0
        try:
            for param in WebServer.expected_put_params:
                param_data = data.get(param, None)
                if param_data:
                    WebServer.put_dict[param] = param_data
                    added += 1
        except Exception as e:
            logger.error(f"Put exception: {e}")
        if added:
            logger.debug(f"Put dict now contains {len(WebServer.put_dict)} items")
            return web.Response(text=f"Put {added} info items")
        else:
            return web.HTTPNoContent(reason=f"Could not add info items", text=f"Did not put any info items")
    
    @routes.post('/data')
    async def info_response(request: web.Request):
        try:
            data = await request.json()
            logger.debug(f"Posting data {data}")
            if len(data):
                WebServer.post_list.append(data)
                logger.debug(f"Post list now contains {len(WebServer.post_list)} items")
                return web.Response(text=f"Posted {data}")
            else:
                return web.HTTPNoContent(reason=f"Could not add info items", text=f"Did not post any info items")
        except Exception as e:
            msg = f"Unable to post data: {e}"
            logger.error(msg)
            return web.HTTPNoContent(reason=msg, text=f"Did not post any info items")

    @routes.post("/command")
    async def command_handler(request: web.Request):
        """
        Python only comment
        This is the RPC plugin for running functions dynamically
        ---
        description: End-point for running functions directly
        tags:
        - RPC
        responses:
            "200":
                description: successfully found and started command
            "400":
                description: function not found
        """
        j_data = await request.json()
        helpers.custom_schema_validation(j_data, ServerSchemas.Command)
        if j_data["name"] in HandlerRegistry:
            t = asyncio.get_event_loop().create_task(HandlerRegistry[j_data["name"]](*j_data["args"], **j_data["kwargs"]))
            WebServer.pending_tasks.append(t)
            return web.Response(text=f"Running {j_data['name']}")
        else:
            logger.error(f"{j_data['name']} not in {HandlerRegistry.keys()}")
            raise web.HTTPNotImplemented(reason=f"Unable to find {j_data['name']}", text=f"Cannot run {j_data['name']}")

    @helpers.register_name("xyz", HandlerRegistry)
    async def do_xyz(self, *args, **kwargs):
        logger.info(f"xyz uses: args '{args}', and keywords '{kwargs}'")
        WebClient().send_done_with_gen()

    async def run_server(self):
        WebServer.app = web.Application(logger=logger, middlewares=[WebServer.middleware])
        fernet_key = fernet.Fernet.generate_key()
        secret_key = base64.urlsafe_b64decode(fernet_key)
        setup(WebServer.app, EncryptedCookieStorage(secret_key))
        # Configure default CORS settings.
        cors = aiohttp_cors.setup(WebServer.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                )
        })
        
        WebServer.app.add_routes(self.routes)  # adds the route table definition, comprising functions with the decorator @route
        # Configure CORS on all routes.
        for route in list(WebServer.app.router.routes()):
            cors.add(route)

        setup_swagger(WebServer.app, contact="brit.cornwell@intel.com", api_version="2.0.0",
                        description="This is the documentation for the engine", title="MARS 2.0 AIOHTTP demo")
        runner = web.AppRunner(WebServer.app)
        await runner.setup()
        WebServer.site = web.TCPSite(runner, '127.0.0.1', 12345)
        await WebServer.site.start()
        logger.info(f"Running async web server at {WebServer.site.name}")
    
    def do_task(loop: asyncio.AbstractEventLoop, task_list: list):
        if len(task_list):
            task = task_list[0]
            if isinstance(task, Tuple):
                WebServer.running_tasks.append(loop.create_task((task[0](*task[1:]))))
            else:
                WebServer.running_tasks.append(loop.create_task((task())))
            return True
        else:
            return False

    async def run_demo():
        logger.info("Starting")
        idle_max = 10
        idle = 0
        should_run = True
        loop = asyncio.get_event_loop()
        wc = WebClient()
        ws = WebServer.create()
        run_task = loop.create_task(ws.run_server())
        tasks = [
                    # wc.send_check,
                    # wc.send_check,
                    # wc.send_ww38,
                    # wc.send_check_post,
                    # (wc.send_post, "randomdata"),
                    # wc.send_check,
                    # wc.send_check_post,
                    # (wc.send_check, {"path": "put"}),
                    # (wc.send_command, "xyz", [1,2,3], {"name": "xyz", "purpose": "running"}),
                    # wc.send_check,
                    # wc.send_check_post,
                    # wc.send_check,
                    # (wc.send_check, {"path": "post"}),
                    # (wc.send_update, "api_ww38"),
                    # wc.send_check,
                    # (wc.send_update, "api_ww39"),
                    # wc.send_check,
                    # wc.send_check,
                    # wc.send_ww38,
                    # wc.send_check,
                    # wc.send_ww39,
                    # wc.send_check,
                ]
        for i in range(1, 100000):
            tasks.append(wc.send_check)
        while should_run:
            if idle_max == 0:
                should_run = False
            else:
                if WebServer.do_task(loop, tasks):
                    logger.info("Performed task")
                    tasks = tasks[1:]
                    idle = 0
                else:
                    idle += 1
                    if idle > idle_max:
                        logger.info("No tasks left!")
                        should_run = False
                    await asyncio.sleep(1)
                    idle_max -= 1
                WebServer.do_task(loop, [wc.send_ping])
        await asyncio.sleep(60)  # just to make sure nothing else is running


#@helpers.decorate_all_methods(client_decorator)
@helpers.decorate_all_methods(helpers.debug_decorator)
class WebClient():
    async def new_session(self):
        return aiohttp.ClientSession()
    
    async def get_response(self, path='/', url="http://127.0.0.1:12345", params=None):
        async with await self.new_session() as session:
            return await session.get(f"{url}{path}", params=params)
    
    async def put_response(self, path='/', url="http://127.0.0.1:12345", data=""):
        async with await self.new_session() as session:
            return await session.put(f"{url}{path}", data=json.dumps(data))

    async def post_response(self, path='/', url="http://127.0.0.1:12345", data=""):
        async with await self.new_session() as session:
                return await session.post(f"{url}{path}", data=json.dumps(data))

    async def print_response(self, resp: aiohttp.ClientResponse):
        if resp.status != requests.codes.ok:
            logger.error(f"Response error: {await resp.text()} from {resp.request_info.method} {resp.request_info.url}")
        else:
            logger.info(f"Response text: {await resp.text()}")

    async def send_ping(self):
        async with await self.get_response(params={"event_id":123}) as resp:
            await self.print_response(resp)
    
    async def send_check(self, params={}):
        async with await self.get_response("/check", params=params) as resp:
            await self.print_response(resp)
    
    async def send_ww38(self):
        async with await self.get_response("/ww38") as resp:
            await self.print_response(resp)
    
    async def send_ww39(self):
        async with await self.get_response("/ww39") as resp:
            await self.print_response(resp)

    async def send_update(self, to_import=None):
        if isinstance(to_import, str):
            to_import = {"file": to_import}
        async with await self.get_response("/update", params=to_import) as resp:
            await self.print_response(resp)
    
    async def send_check_post(self):
        async with await self.get_response("/check/post") as resp:
            await self.print_response(resp)
    
    async def send_check_put(self):
        async with await self.get_response("/check/put") as resp:
            await self.print_response(resp)

    async def send_put(self, data=""):
        async with await self.put_response("/data", data=data) as resp:
            await self.print_response(resp)

    async def send_post(self, data=""):
        async with await self.post_response("/data", data=data) as resp:
            await self.print_response(resp)

    async def send_command(self, name="", args=[], kwargs={}):
        async with await self.post_response("/command", data={"name": name, "args": args, "kwargs": kwargs}) as resp:
            await self.print_response(resp)
 

if __name__ == "__main__":
    # if "apis" in sys.argv:
    #     self.update(apis)
    helpers.generate_docs("docs/html", os.path.basename(__file__))
    asyncio.run(WebServer.run_demo())
    