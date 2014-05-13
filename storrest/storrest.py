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
    'storcli_command': '/opt/MegaRAID/storcli/storcli64'
}

app = web.application(urls, globals())


def get_storcli():
    print('get_storcli: storcli_command: %s' % CFG['storcli_command'])
    return storcli.Storcli(storcli_cmd=CFG['storcli_command'])


def jsonize(fcn):
    def wrapper(*args, **kwargs):
        web.header('Content-Type', 'application/json')
        return json.dumps(fcn(*args, **kwargs))
    return wrapper


class ControllersView(object):
    def __init__(self):
        self.storcli = get_storcli()

    @jsonize
    def GET(self):
        return self.storcli.controllers


class ControllerDetails(object):
    def __init__(self):
        self.storcli = get_storcli()

    @jsonize
    def GET(self, controller_id):
        return self.storcli.controller_details(controller_id)


class PhysicalDrivesView(object):
    def __init__(self):
        self.storcli = get_storcli()

    @jsonize
    def GET(self, controller_id=None):
        return self.storcli.physical_drives(controller=controller_id)


class VirtualDrivesView(object):
    def __init__(self):
        self.storcli = get_storcli()

    @jsonize
    def GET(self, controller_id=None):
        return self.storcli.virtual_drives(controller=controller_id)

    @jsonize
    def POST(self, controller_id):
        raw_data = web.data()
        data = json.loads(raw_data)
        web.ctx.status = '201 Created'
        params = {'raid_level': data.get('raid_level', 0),
                  'spare_drives': data.get('spare_drives'),
                  'strip_size': data.get('strip_size'),
                  'name': data.get('name'),
                  'read_ahead': data.get('read_ahead'),
                  'write_cache': data.get('write_cache'),
                  'io_policy': data.get('io_policy')
                  }
        return self.storcli.create_virtual_drive(data['drives'], **params)


class VirtualDriveDetails(object):
    def __init__(self):
        self.storcli = get_storcli()

    @jsonize
    def GET(self, controller_id, virtual_drive_id):
        return self.storcli.virtual_drive_details(int(controller_id),
                                                  int(virtual_drive_id))

    @jsonize
    def DELETE(self, controller_id, virtual_drive_id):
        return self.storcli.delete_virtual_drive(controller_id,
                                                 virtual_drive_id,
                                                 force=True)


if __name__ == '__main__':
    app.run()
