from aiohttp import web

# from agnostic_event_handling import decorate_all_methods
# from aiohttp_server import client_decorator, server_decorator

routes = web.RouteTableDef()

class Executor:
    _instance = None
    def __init__(self):
        self.val = 1
    
    def execute(self):
        return True
    
    def format_test_data():
        return True

Managers = {"execution", Executor()}


#@decorate_all_methods(server_decorator)
class CustomRouteTable:
    @routes.get('/ww38')  # optional decorator, can be replaced by manually adding the route via app.add_routes([web.get(/', func)])
    async def basic_response(request):
        return web.Response(text="ww38 works")

    @routes.get('/ww38/check')  # custom path
    async def check_response(request):
        Executor.format_test_data()
        return web.Response(text="checkcheck")

    @routes.get('/ww38/execute')
    async def check_response(request):
        Managers["execution"].execute()
        return web.Response(text="ww38 execute works")