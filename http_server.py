import asyncio
import json
import pathlib
import datetime

from aiohttp import web

class HttpServer:

    def __init__(self):
        self.start_time = datetime.datetime.now()
        self.application = None
        self.core = None
        self.json_indent = 4

    #
    # Runtime Handlers
    #
    async def handle_maintenance_status(self, request):
        delta = round((datetime.datetime.now() - self.start_time).total_seconds())

        response_obj = {
            'version': self.core.version,
            'uptime': str(datetime.timedelta(seconds=delta)), 
            'status': 'success'
        }
        return web.Response(text=self.to_json(response_obj))

    async def handle_maintenance_restart(self, request):
        self.core.restart = True
        self.core.running = False
        response_obj = {'status': 'success'}
        return web.Response(text=self.to_json(response_obj))

    async def handle_maintenance_shutdown(self, request):
        self.core.running = False
        response_obj = {'status': 'success'}
        return web.Response(text=self.to_json(response_obj))

    #
    # Device Handlers
    #
    async def handle_device_list(self, request):
        devices = self.core.get_devices()
        groups = self.core.get_groups()
        records_json = []

        for current in devices:
            name = current["name"]
            group = 'Home'

            group_candidates = [current for current in groups if name.startswith(current)]
            if len(group_candidates) > 0:
                group = group_candidates[0]

            element = {
                'id': current["id"],
                'name': name,
                'group': group
            }
            records_json.append(element)

        response_obj = {
            'status': 'ok',
            'groups': groups,
            'devices': records_json
        }
        return web.Response(text=self.to_json(response_obj))

    async def handle_device_action(self, request, device_id, action):
        result = await self.core.run_device_action(device_id, action)
        response_obj = {
            'status': 'ok' if result else "error"
        }
        return web.Response(text=self.to_json(response_obj))

    async def handle_device_enable(self, request):
        return await self.handle_device_action(request, request.match_info['id'], "enable")

    async def handle_device_disable(self, request):
        return await self.handle_device_action(request, request.match_info['id'], "disable")

    async def handle_device_open(self, request):
        return await self.handle_device_action(request, request.match_info['id'], "open") 

    async def handle_device_close(self, request):
        return await self.handle_device_action(request, request.match_info['id'], "close") 

    async def handle_device_stop(self, request):
        return await self.handle_device_action(request, request.match_info['id'], "stop")         

    def json_converter(o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()

    def to_json(self, data):
        return json.dumps(data, indent=self.json_indent, default=HttpServer.json_converter)

    #
    # Pump
    #
    async def run(self, core):
        port = core.configuration["HttpServer"]["port"]
        self.start_time = datetime.datetime.now()

        core.log(f"HttpServer starting pump on {port}...")
        self.core = core
        self.application = web.Application()

        self.application.router.add_get("/api/maintenance/status", self.handle_maintenance_status)
        self.application.router.add_get("/api/maintenance/shutdown", self.handle_maintenance_shutdown)
        self.application.router.add_get("/api/maintenance/restart", self.handle_maintenance_restart)

        self.application.router.add_get("/api/device/list", self.handle_device_list)

        self.application.router.add_get("/api/device/{id}/enable", self.handle_device_enable)
        self.application.router.add_get("/api/device/{id}/disable", self.handle_device_disable)

        self.application.router.add_get("/api/device/{id}/open", self.handle_device_open)        
        self.application.router.add_get("/api/device/{id}/close", self.handle_device_close)  
        self.application.router.add_get("/api/device/{id}/stop", self.handle_device_stop) 

        root = pathlib.Path(__file__).parent
        self.application.router.add_static('/', path=root / 'static', name='static')

        runner = web.AppRunner(self.application)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', port)
        await site.start()

        # pump
        while core.running:
            await asyncio.sleep(1)

        core.log("HttpServer Shutting down")
        await runner.cleanup()
