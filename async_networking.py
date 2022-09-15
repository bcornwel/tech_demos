"""
This file is an example of asynchronous networking using the asyncio library
"""

import asyncio, inspect, aiohttp
from aiohttp import web
import logging


logging.basicConfig(filename="test.log", level=logging.INFO)
logger = logging.getLogger('test_log')
logger.info("async networking")


class tasks():
    """
    class that demonstrates how async tasks work
    """
    BACKGROUND_TASKS = set()  # container for tasks to ensure they don't get lost

    def get_func_name(self):
        """
        prints the name of the function that calls this function
        """
        try:
            return inspect.stack()[1][3]
        except:
            return "Unknown function"

    def finished(self, obj):
        """
        prints finished with the task name
        """
        print(f"Finished with task '{obj.get_name()}'")

    async def say_after(self, message, delay=1):
        """
        prints after a delay
        """
        await asyncio.sleep(delay)
        print(message)

    async def long_runner(self):
        """
        runs a series of tasks
        """
        for i in range(5):
            print(f"Tick {i}")
            await asyncio.sleep(1)  # will unblock for a moment for other tasks to run

    async def task_runner(self):
        """
        runs a long-running task as well as a shorter one to demonstrate tasks working asynchronously
        """
        long_running_task = asyncio.create_task(self.long_runner(), name="Long Running Task")
        self.BACKGROUND_TASKS.add(long_running_task)
        long_running_task.add_done_callback(self.finished)
        long_running_task.add_done_callback(self.BACKGROUND_TASKS.discard)
        task1 = asyncio.create_task(self.say_after('hello', 1), name="Say Hello")  # creates a task based on the function which can be scheduled
        self.BACKGROUND_TASKS.add(task1)  # save the reference to the task in case it gets dereferenced so it won't be discarded in garbage collection
        task1.add_done_callback(self.finished)  # adds a callback to print finished with the task - would get called if task1 never started before program end
        task1.add_done_callback(self.BACKGROUND_TASKS.discard)  # adds a callback to discard the list of background tasks
        await task1  # will wait for the task to complete
        print(f"{self.get_func_name()} complete")
        await long_running_task

    async def test(self):
        print("Empty function")

    async def test_tasks(self):
        task1 = asyncio.create_task(self.task_runner())
        task2 = asyncio.create_task(self.test())
        await task2
        await task1

    async def run(self):
        await self.test_tasks()
        print("Tasks done")


class EchoServerProtocol(asyncio.Protocol):
    """
    simple tcp server protocol
    """
    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(peername))
        self.transport = transport

    def data_received(self, data):
        message = data.decode()
        print('Data received: {!r}'.format(message))

        print('Send: {!r}'.format(message))
        self.transport.write(data)

        print('Close the client socket')
        self.transport.close()


class EchoClientProtocol(asyncio.Protocol):
    """
    simple tcp client protocol
    """
    def __init__(self, message, on_con_lost):
        self.message = message
        self.on_con_lost = on_con_lost

    def connection_made(self, transport):
        transport.write(self.message.encode())
        print('Data sent: {!r}'.format(self.message))

    def data_received(self, data):
        print('Data received: {!r}'.format(data.decode()))

    def connection_lost(self, exc):
        print('The server closed the connection')
        self.on_con_lost.set_result(True)


class networking():
    server_task = None
    server = None

    async def start_server(self):
        """
        creates a tcp server
        """
        loop = asyncio.get_running_loop()

        self.server = await loop.create_server(
            lambda: EchoServerProtocol(),
            '127.0.0.1', 8888)

        async with self.server:
            await self.server.serve_forever()

    async def stop_server(self):
        """
        stops the running tcp server
        """
        # asyncio.get_running_loop().stop()
        if self.server:
            self.server.close()

    async def start_client(self):
        """
        creates a tcp client that connects to the server and says hello world
        """
        # Get a reference to the event loop as we plan to use
        # low-level APIs.
        loop = asyncio.get_running_loop()

        on_con_lost = loop.create_future()
        message = 'Hello World!'

        transport, protocol = await loop.create_connection(
            lambda: EchoClientProtocol(message, on_con_lost),
            '127.0.0.1', 8888)

        # Wait until the protocol signals that the connection
        # is lost and close the transport.
        try:
            await on_con_lost
        finally:
            transport.close()

    def run(self):
        self.server_task = asyncio.create_task(self.start_server())
        asyncio.run(self.start_client())


class WebServer():
    routes = web.RouteTableDef()

    @routes.get('/')  # optional decorator, can be replaced by manually adding the route via app.add_routes([web.get(/', func)])
    async def basic_response(request):
        return web.Response(text="Hello")
    
    @routes.get('/check')  # custom path
    async def check_response(request):
        return web.Response(text="checkcheck")
    
    async def run_server(self):
        app = web.Application()
        app.add_routes(self.routes)  # adds the route table definition, comprising functions with the decorator @route
        # app.add_routes([web.get('/', basic_response)])  # could add a list of routes all at once

        # web.run_app(app)  # runs the web app synchronously
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '127.0.0.1', 12345)
        await site.start()
        print("Running async web server")


class WebClient():
    async def new_session(self):
        return aiohttp.ClientSession()

    async def get_response(self, path='/', url="http://127.0.0.1:12345"):
        async with await self.new_session() as session:
            return await session.get(f"{url}{path}")

    async def print_response(self, resp):
        print("Response text: ", await resp.text())

    async def send_ping(self):
        async with await self.get_response() as resp:
            await self.print_response(resp)
    
    async def send_check(self):
        async with await self.get_response("/check") as resp:
            await self.print_response(resp)


class website():
    async def run():
        t = tasks()
        n = networking()
        tasks_task = asyncio.create_task(t.run())
        ws = WebServer()
        n_server = asyncio.create_task(n.start_server())
        wc = WebClient()
        await ws.run_server()
        await asyncio.sleep(1)
        n_client = asyncio.create_task(n.start_client())
        await asyncio.sleep(1)
        print("Sending ping")
        loop = asyncio.get_event_loop()
        ping_task = loop.create_task(wc.send_ping())  # creates a task to ping the server that fires off immediately without waiting
        print("Sent ping")
        await asyncio.sleep(2)
        await wc.send_check()
        print("Website tasks done")
        await asyncio.sleep(1)
        await n_client
        await tasks_task
        await n.stop_server()


if __name__ == "__main__":
    t = tasks
    # asyncio.run(t.run())
    #n = networking
    # asyncio.run(n.run())
    w = website
    asyncio.run(w.run())