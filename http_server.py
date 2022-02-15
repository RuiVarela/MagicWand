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
            'update': str(datetime.timedelta(seconds=delta)), 
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
        devices = await self.core.database.getDevices()
        records_json = [record.to_dic() for record in devices]

        response_obj = {
            'status': 'ok',
            'devices': records_json
        }
        return web.Response(text=self.to_json(response_obj))

    async def handle_device_delete(self, request):
        device_id = request.match_info['id']
        await self.core.database.deleteDevice(device_id)

        response_obj = {'status': 'ok'}
        return web.Response(text=self.to_json(response_obj))

    def json_converter(o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()

    def to_json(self, data):
        return json.dumps(data, indent=self.json_indent, default=HttpServer.json_converter)

    #
    # Pump
    #
    async def run(self, core):
        port = core.configuration["http_server"]["port"]
        self.start_time = datetime.datetime.now()

        print(f"HttpServer starting pump on {port}...")
        self.core = core
        self.application = web.Application()

        self.application.router.add_get("/api/maintenance/status", self.handle_maintenance_status)
        self.application.router.add_get("/api/maintenance/shutdown", self.handle_maintenance_shutdown)
        self.application.router.add_get("/api/maintenance/restart", self.handle_maintenance_restart)

        self.application.router.add_get("/api/device/list", self.handle_device_list)
        self.application.router.add_get("/api/device/{id}/delete", self.handle_device_delete)

        root = pathlib.Path(__file__).parent
        self.application.router.add_static('/', path=root / 'static', name='static')

        runner = web.AppRunner(self.application)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', port)
        await site.start()

        # pump
        while core.running:
            await asyncio.sleep(1)

        print("HttpServer Shutting down")
        await runner.cleanup()
