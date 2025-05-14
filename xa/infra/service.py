"""
This is a POC service/engine
It only contains routes required to have access to Service class data, otherwise routes are imported, e.g. from service_routes.py
"""


import queue
import aiohttp
from aiohttp import web
import aiohttp_cors
from aiohttp_session import setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from aiohttp_swagger import setup_swagger
from aiohttp.web_runner import GracefulExit
import asyncio
import base64
from cryptography import fernet
from datetime import datetime
from inspect import iscoroutinefunction, isfunction
import logging
from os import path
import requests
import sys
import time
import traceback
from typing import Awaitable, Callable, Sequence, Tuple
import webbrowser


from framework.arg_utils import _parse_args, Namespace, SERVICE_PARSER, parse_manager_args, handle_base_args
from framework.definitions import Const
from framework import doc_utils
from framework import forwarder
from framework import log_utils
from framework.service_routes import routes as s_routes, ServiceAdapter
from framework.client import Client, MarsHeaders
from framework.decorators import debug_decorator, exception_decorator, decorate_all_methods
from framework.manager import ManagerPurposes, get_managers
from framework.sys_utils import url_parts_to_url, set_mars_exit_handler


class ServiceTask:
    """
    This class is meant to wrap tasks with their args
    """
    def __init__(self, func:Callable, args:Sequence=[], kwargs:dict={}) -> None:
        self.func = func
        self.args = args
        self.kwargs = kwargs


# @decorate_all_methods(debug_decorator, logging.getLogger(Const.MarsLogName))
@decorate_all_methods(exception_decorator, logging.getLogger(Const.MarsLogName))
class Service:
    """
    This is the core service, more or less equivalent to the "engines" of mars1
    It does the heavy lifting for route and task mangement
    Standalone, there's not much use for it, other than viewing documentation
    To make use of it, import routes and add them when building the service

    Raises:
        GracefulExit: the shutdown exception
    """
    _instance = None
    site = None

    def __init__(self, host:str, port:int, args:Namespace, routes:list=None, logger:logging.Logger=None, log_buffer:log_utils.TailLogger=None, log_name:str=None):
        set_mars_exit_handler()  # this is the earliest common point for execution to start, and therefore a good place to set up exit handling (cleanup, shutdown, etc)
        self.host = host
        self.port = port
        self.log_name = log_name if log_name else Const.MarsLogName
        self.logger = logger if logger else logging.getLogger(self.log_name)
        if log_buffer:
            self.log_buffer = log_buffer
        else:
            _, self.log_buffer = log_utils.get_mars_log(self.logger, get_tail=True, log_level=args.log_level if args else logging.INFO)
        self.args = args
        self.started = False
        self.should_run = True
        self.app = None
        self.tasks = asyncio.Queue(-1)
        self.running_tasks = list()
        self.route_tables = []
        self.log_reload = 5000
        self.loop = asyncio.get_event_loop()
        if isinstance(routes, list):
            for route_table in routes:
                if isinstance(route_table, web.RouteTableDef):
                    self.route_tables.append(route_table)
                else:
                    raise TypeError(f"Cannot add routes because {type(route_table)} is not a web.RouteTableDef")
        elif isinstance(routes, web.RouteTableDef):
            self.route_tables.append(routes)
        else:
            raise TypeError(f"Cannot add routes because {type(routes)} is not a web.RouteTableDef")
        Service._instance = self
        self.forwarding_task = None
        self.client = Client(self.host, self.port)
        self.peers = set()
        self.managers = dict()
        ServiceAdapter.instance = self

    def build_service_task(self, func:Callable, args:Sequence=[], kwargs:dict={}) -> ServiceTask:
        """
        Creates a new service task

        To be used by routes and external files that might have circular references

        Args:
            func (Callable): the function to run
            args (Sequence, optional): *args. Defaults to [].
            kwargs (dict, optional): **kwargs. Defaults to {}.

        Returns:
            ServiceTask: the created service task
        """
        return ServiceTask(func, args, kwargs)

    @web.middleware
    async def middleware(request: web.Request, handler: Callable[[web.Request], Awaitable[web.Response]]) -> web.Response:
        """
        This function is a decorator for server functions which is handled better than a standard decorator

        Args:
            request (web.Request): the original request
            handler (Callable[[web.Request], Awaitable[web.Response]]): The handler to be called

        Returns:
            web.Response: The response to send back to the client
        """
        try:
            resp = await handler(request)
            for header in MarsHeaders._list:
                resp.headers[header] = request.headers.get(header, "")  # ensure the header comes back so that we have better tracking on the event
            resp.enable_compression()
            return resp
        except OSError:
            Service._instance.logger.warn(f"{request.host} disconnected mid connection")
        except Exception as server_exception:
            msg = f"Server error for {request.method} {request.url}: {server_exception}: {traceback.format_exc()}"
            Service._instance.logger.error(msg)
            return aiohttp.ClientResponseError(request_info=aiohttp.RequestInfo(request.url, method=request.method, headers=request.headers), history=[],
                                                   status=requests.codes.server_error, message=msg, headers=request.headers)

    async def on_shutdown(app:web.Application):
        """
        the shutdown handler
        this is where one would stop service processes of any sort, or send out last messages

        Args:
            crap (web.Application): the webserver application
        """
        while Service._instance.running_tasks.not_empty:
            task = Service._instance.running_tasks.get()
            task.cancel()

    async def start_server(self, doc:str=None, title:str=None):
        """
        Starts a tcp server after having build the service object

        Args:
            doc (str, optional): doc to display on the swagger page. Defaults to None.
            title (str, optional): title to display on the swagger page. Defaults to None.
        """
        try:
            self.app = web.Application(logger=self.logger, middlewares=[Service.middleware])
            self.app.on_shutdown.append(Service.on_shutdown)
            setup(self.app, EncryptedCookieStorage(base64.urlsafe_b64decode(fernet.Fernet.generate_key())))
            # Configure default CORS settings.
            cors = aiohttp_cors.setup(self.app, defaults={
                "*": aiohttp_cors.ResourceOptions(
                        allow_credentials=True,
                        expose_headers="*",
                        allow_headers="*",
                    )
            })
            for route_table in self.route_tables:
                self.app.add_routes(route_table)  # adds the route table definition, comprising functions with a route decorator
            # Configure CORS on all routes.
            for route in list(self.app.router.routes()):
                cors.add(route)
            title = path.basename(sys.argv[0])[:-3] if not title else title.replace(".log", "")
            title = "MARS 2 " + title
            # setup the swagger documentation which is available at /docs/api
            setup_swagger(self.app, contact=doc_utils.CONTACT, api_version=doc_utils.API,
                            description=__doc__ if not doc else doc, title=title,)
            runner = web.AppRunner(self.app)
            await runner.setup()
            Service.site = web.TCPSite(runner, self.host, self.port)
            await Service.site.start()
            self.logger.info(f"Running {__file__[:-3]} at {Service.site.name}")
            try:
                self.forwarding_task = forwarder.run_forwarding(logger=self.logger, loop=self.loop, asynchronous=True)
            except Exception as forwarding_exception:
                self.logger.error(f"Error running forwarding service. {__file__} can still run: {forwarding_exception}")
            self.started = True
        except Exception as start_exception:
            self.logger.error(f"Error starting service: {start_exception}")
            raise start_exception
    
    def build(host:str=None, port:int=None, args:Namespace=None, routes:web.RouteTableDef or Sequence[web.RouteTableDef]=None, logger:logging.Logger=None, log_buffer:log_utils.TailLogger=None, log_name:str=None):
        """
        Builds an instance of the service

        Args:
            host (str, optional): the host name e.g. 127.0.0.1. Defaults to None.
            port (int, optional): the port to use. Defaults to None.
            args (Namespace, optional): the command line arg data. Defaults to None.
            routes (web.RouteTableDeforSequence[web.RouteTableDef], optional): the route table(s) to pull in. Defaults to None.
            logger (logging.Logger, optional): logger instance for writing to the log. Defaults to None.
            log_buffer (log_utils.TailLogger, optional): the log buffer instance used for dumping logs to variables. Defaults to None.
            log_name (str, optional): the name of the log. Defaults to None.

        Returns:
            Service: the instance of the Service
        """
        if isinstance(routes, list):
            routes.append(s_routes)
        elif routes:
            routes = [routes, s_routes]
        else:
            routes = [s_routes]
        return Service(host, port, args, routes, logger, log_buffer, log_name)
    
    async def do_task(self, task: ServiceTask) -> asyncio.Task or any:
        """
        Runs a ServiceTask with provided parameters if any

        Args:
            task (ServiceTask): The task object to run including the function and optional args/kwargs

        Returns:
            asyncio.Task or any: the asyncio Task object which is running asynchronously
        """
        assert isinstance(task, ServiceTask), "Task in queue is not a ServiceTask!"
        if iscoroutinefunction(task.func):
            try:
                future:asyncio.Task = task.func(*task.args, **task.kwargs)
                self.running_tasks.append(future)
                res = await future
                self.running_tasks.remove(future)
                return res
            except Exception as coro_error:
                self.logger.error(f"Unable to do coroutine task '{task.func}'", exc_info=coro_error)
        elif isfunction(task.func):
            try:
                return task.func(*task.args, **task.kwargs)
            except Exception as func_error:
                self.logger.error(f"Unable to do function task '{task.func}'", exc_info=func_error)

    async def run_core(self, forever:bool=True, duration:int=0):
        """
        Runs the core loop of the service

        Args:
            forever (bool, optional): Whether or not to run forever. Defaults to True.
            duration (int, optional): How long to run for (in seconds). Defaults to 0.
        """
        try:
            startup_timeout = 10
            while not self.started and startup_timeout:
                await asyncio.sleep(1)
                startup_timeout -= 1
            if not startup_timeout and not self.started:
                raise Exception("Service never started!")
            idle_max = 8*3600  # 8 hours
            idle = 0
            sleep_interval = .5
            start_time = time.perf_counter()
            run_time = 0
            while self.should_run and (forever or run_time < duration):
                run_time = time.perf_counter() - start_time
                self.logger.debug(f"Running for {run_time}")
                try:
                    try:
                        task = self.tasks.get_nowait()
                        await self.do_task(task)
                    except asyncio.QueueEmpty:
                        idle += sleep_interval
                        if idle > idle_max:
                            self.should_run = False
                        await asyncio.sleep(sleep_interval)
                except Exception as task_exception:
                    self.logger.error(f"Exception in service task loop {task_exception}")
        except Exception as core_exception:
            self.logger.error(f"Exception in service core: {core_exception}")
        self.logger.info("Finished running service core")
        raise GracefulExit("Shutting down after finished running")
         
    def run_server(self, forever:bool=True, duration:int=0, asynchronously:bool=False, doc:str=None, title:str=None) -> None or Tuple[asyncio.Task, asyncio.Task]:
        """
        Run the server for the duration described.
        If asynchronously is True, this is not a blocking call, otherwise, normally it is blocking

        Args:
            forever (bool, optional): whether or not to run forever. Defaults to True.
            duration (int, optional): how long to run for (in seconds). Defaults to 0.
            asynchronously (bool, optional): Whether or not to run asynchronously. Defaults to False.
            doc (str, optional): doc to display on the swagger page. Defaults to None.
            title (str, optional): title to display on the swagger page. Defaults to None.

        Returns:
            None or Tuple[asyncio.Task, asyncio.Task]: if async, returns the start and run task handles
        """
        if asynchronously:
            start_task = self.loop.create_task(self.start_server(doc, title))
            run_task = self.loop.create_task(self.run_core(forever=forever, duration=duration))
            return start_task, run_task
        else:
            start_task = self.loop.create_task(self.start_server(doc, title))  # doesn't seem to start even though the previous block works
            asyncio.run(self.run_core(forever=forever, duration=duration))
            start_task.cancel()

def run_service(service:Service=None, args:Namespace=None, routes:web.RouteTableDef or Sequence[web.RouteTableDef]=None, doc:str=None, log_name:str=Const.MarsLogName, managers:dict=None, ignore_unknown:bool=False):
    """
    Runs the service. essentially just the main entry point for the service to start, to be called by the __main__ from mars, exe, gen, etc

    Args:
        service (Service, optional): an existing service object to reuse. Defaults to None.
        args (NameSpace, optional): the parsed arguments coming from the arg parser. Defaults to None.
        routes (web.RouteTableDeforSequence[web.RouteTableDef], optional): the route table(s) to pull in. Defaults to None.
        doc (str, optional): the doc string, currently just for swagger. Defaults to None.
        log_name (str, optional): the name of the log file. Defaults to Const.MarsLogName if None.
        managers (dict, optional): the manager dictionary to add to this service
        ignore_unknown (bool, optional): Whether or not to ignore unknown arguments (generally for testing). Defaults to False.
    """
    log_name = log_name if log_name and ".log" not in log_name else f"{log_name if log_name else __file__[:-3]}.log"
    service = service if service else build_service(args=args, routes=routes, log_name=log_name, ignore_unknown=ignore_unknown)
    title = path.basename(log_name if log_name else __file__)[:-4]
    start_task, run_task = service.run_server(forever=not args.test_mode, duration=5 if args.test_mode else 0,
                                                asynchronously=True, doc=doc, title=title)
    try:
        service.loop.run_forever()
    except GracefulExit as e:
        print(e)
        sys.exit(0)


def build_service_and_args(manager_purpose:str=None, args:Namespace=None, routes:web.RouteTableDef or Sequence[web.RouteTableDef]=None, log_name:str=Const.MarsLogName, ignore_unknown:bool=False) -> Tuple[Service, Namespace]:
    """
    Creates a service object, and instantiates the parsed args with provided manager data
    will handle the parsed args, such as version

    Args:
        manager_purpose (str, optional): the manager to instantiate. Defaults to None.
        args (Namespace, optional): an arg namespace to use. Defaults to None.
        routes (RouteTableDef or Sequence[RouteTableDef], optional): the routes to include if any. Defaults to None.
        log_name (str, optional): a log name, usually the manager name. Defaults to Const.MarsLogName.
        ignore_unknown (bool, optional): Whether or not to ignore unknown arguments (generally for testing). Defaults to False.

    Returns:
        Tuple[Service, Namespace]: the service and arg namespace
    """
    args = args if args else _parse_args(SERVICE_PARSER) 
    if manager_purpose and manager_purpose not in args.managers:
        args.managers.append(manager_purpose)
    args = parse_manager_args(args.managers, args)
    handle_base_args(args)
    return build_service(args=args, routes=routes, log_name=log_name, ignore_unknown=ignore_unknown), args


def run_standard_service(manager_purpose:str=None, doc:str=None, log_name:str=Const.MarsLogName, service:Service=None, args:Namespace=None, ignore_unknown:bool=False):
    """
    Useful for simple services that don't need to do any special work on startup

    Args:
        manager_purpose (str, optional): a manager purpose such as ui, gen, etc. Defaults to None.
        doc (str, optional): the doc string to use for the manager/service. usually should be __doc__. Defaults to None.
        log_name (str, optional): the log name for the manager/service, use Const.[your manager]LogName for this. Defaults to Const.MarsLogName.
        service (Service, optional): existing service to use. Defaults to None.
        args (Namespace, optional): exksting args to use. Defaults to None.
        ignore_unknown (bool, optional): Whether or not to ignore unknown arguments (generally for testing). Defaults to False.
    """
    if not service and not args:
        service, args = build_service_and_args(manager_purpose=manager_purpose, log_name=log_name, ignore_unknown=ignore_unknown)
    elif service and not args:
        args = args if args else _parse_args(SERVICE_PARSER) 
        if manager_purpose and manager_purpose not in args.managers:
            args.managers.append(manager_purpose)
        args = parse_manager_args(args.managers, args, ignore_unknown=ignore_unknown)
    elif args and not service:
        service = build_service(args=args, log_name=log_name, ignore_unknown=ignore_unknown)
        handle_base_args(args)
    doc = (doc if doc else "") + f"\nRoutes included for {', '.join(args.managers) + ' and base service' if args.managers else 'base service'}"
    managers = get_managers(args.managers)
    run_service(service=service, args=args, doc=doc, log_name=log_name, managers=managers)


if __name__ == "__main__":
    run_standard_service(doc=__doc__)
