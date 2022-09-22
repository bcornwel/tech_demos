from aiohttp import web

routes = web.RouteTableDef()

@routes.get('/')  # optional decorator, can be replaced by manually adding the route via app.add_routes([web.get(/', func)])
async def basic_response(request):
    return web.Response(text="Hello")

@routes.get('/ww39')  # custom path
async def check_response(request):
    return web.Response(text="ww39 works")