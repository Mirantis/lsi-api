#!/usr/bin/env python

import json
import web

import storcli

urls = (
    '/v0.5/controllers', 'ControllersView',
    '/v0.5/controllers/([0-9]+)', 'ControllerDetails',
    '/v0.5/controllers/([0-9]+)/physicaldevices', 'PhysicalDrivesView',
    '/v0.5/controllers/([0-9]+)/virtualdevices', 'VirtualDrivesView',
    '/v0.5/controllers/([0-9]+)/virtualdevices/([0-9]+)', 'VirtualDriveDetails',
    #'/v1/servers/0/controllers/([0-9]+)/physicaldevices/([0-9]+)', 'PhysicalDriveInfo',
)

CFG = {
    'storcli_command': ['/opt/MegaRAID/storcli/storcli64']
}

app = web.application(urls, globals())


def get_storcli():
    print('get_storcli: storcli_command: %s' % CFG['storcli_command'])
    return storcli.Storcli(storcli_cmd=CFG['storcli_command'])


def dumb_error_handler(fcn):
    def wrapper(*args, **kwargs):
        try:
            return {'error_code': 0,
                    'error_message': None,
                    'data': fcn(*args, **kwargs)}
        except storcli.StorcliError, e:
            web.ctx.status = '500 Internal Server Error'
            return {'error_code': e.error_code,
                    'error_message': e.message,
                    'data': None}
    return wrapper


def jsonize(fcn):
    def wrapper(*args, **kwargs):
        web.header('Content-Type', 'application/json')
        return json.dumps(fcn(*args, **kwargs))
    return wrapper


class ControllersView(object):
    def __init__(self):
        self.storcli = get_storcli()

    @jsonize
    @dumb_error_handler
    def GET(self):
        return self.storcli.controllers


class ControllerDetails(object):
    def __init__(self):
        self.storcli = get_storcli()

    @jsonize
    @dumb_error_handler
    def GET(self, controller_id):
        return self.storcli.controller_details(controller_id)


class PhysicalDrivesView(object):
    def __init__(self):
        self.storcli = get_storcli()

    @jsonize
    @dumb_error_handler
    def GET(self, controller_id=None):
        return self.storcli.physical_drives(controller=controller_id)


class VirtualDrivesView(object):
    def __init__(self):
        self.storcli = get_storcli()

    @jsonize
    @dumb_error_handler
    def GET(self, controller_id=None):
        return self.storcli.virtual_drives(controller=controller_id)

    @jsonize
    @dumb_error_handler
    def POST(self, controller_id):
        raw_data = web.data()
        data = json.loads(raw_data)
        web.ctx.status = '201 Created'
        param_names = ('raid_level', 'spare_drives', 'strip_size',
                       'name', 'read_ahead', 'write_cache', 'io_policy')
        params = dict([(k, data.get(k)) for k in param_names])
        return self.storcli.create_virtual_drive(data['drives'], **params)


class VirtualDriveDetails(object):
    def __init__(self):
        self.storcli = get_storcli()

    @jsonize
    @dumb_error_handler
    def GET(self, controller_id, virtual_drive_id):
        return self.storcli.virtual_drive_details(int(controller_id),
                                                  int(virtual_drive_id))

    @jsonize
    @dumb_error_handler
    def DELETE(self, controller_id, virtual_drive_id):
        return self.storcli.delete_virtual_drive(controller_id,
                                                 virtual_drive_id,
                                                 force=True)

    @jsonize
    @dumb_error_handler
    def POST(self, controller_id, virtual_drive_id):
        data = json.loads(web.data())
        param_names = ('name', 'read_ahead', 'write_cache', 'io_policy')
        params = dict([(k, data.get(k)) for k in param_names])
        return self.storcli.update_virtual_drive(int(controller_id),
                                                 int(virtual_drive_id),
                                                 **params)

if __name__ == '__main__':
    app.run()
