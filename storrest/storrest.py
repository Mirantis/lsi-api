#!/usr/bin/env python
# Copyright 2014 Avago Technologies Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this software except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import web

from storcli import Storcli, StorcliError

try:
    from storversion import storrest_git_version
except ImportError:
    from gitversion import get_git_version
    storrest_git_version = get_git_version()

urls = (
    '/v0.5/controllers', 'ControllersView',
    '/v0.5/controllers/((?:\d+)|(?:all))', 'ControllerDetails',
    '/v0.5/controllers/([0-9]+)/physicaldevices', 'PhysicalDrivesView',
    '/v0.5/controllers/([0-9]+)/virtualdevices', 'VirtualDrivesView',
    '/v0.5/controllers/([0-9]+)/virtualdevices/([0-9]+)', 'VirtualDriveDetails',
    '/v0.5/controllers/(\d+)/physicaldevices/(\d+)/(\d+)/hotspare', 'HotspareOps',
    '/v0.5/controllers/(\d+)/virtualdevices/((?:cachecade)|(?:nytrocache))', 'CachecadeView',
    '/v0.5/controllers/(\d+)/virtualdevices/((?:cachecade)|(?:nytrocache))/(\d+)', 'CachecadeDetails',
    '/v0.5/controllers/(\d+)/virtualdevices/warpdrive', 'WarpdriveView'
)

CFG = {
    'storcli_command': ['/opt/MegaRAID/nytrocli/nytrocli64']
}

web.config.debug = False
app = web.application(urls, globals())


def get_storcli():
    print('get_storcli: storcli_command: %s' % CFG['storcli_command'])
    return Storcli(storcli_cmd=CFG['storcli_command'])


def dumb_error_handler(fcn):
    def wrapper(*args, **kwargs):
        try:
            return {'error_code': 0,
                    'error_message': None,
                    'storrest_version': storrest_git_version,
                    'data': fcn(*args, **kwargs)}
        except StorcliError, e:
            web.ctx.status = '500 Internal Server Error'
            return {'error_code': e.error_code,
                    'error_message': e.message,
                    'storrest_version': storrest_git_version,
                    'data': None}
    return wrapper


def jsonize(fcn):
    def wrapper(*args, **kwargs):
        web.header('Content-Type', 'application/json')
        return json.dumps(fcn(*args, **kwargs))
    return wrapper


def get_post_data():
    raw_data = web.data()
    try:
        return json.loads(raw_data)
    except:
        raise StorcliError(error_code=400, msg='invalid JSON')


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
        return self.storcli.physical_drives(controller_id=controller_id)


class VirtualDrivesView(object):
    def __init__(self):
        self.storcli = get_storcli()

    @jsonize
    @dumb_error_handler
    def GET(self, controller_id=None):
        return self.storcli.virtual_drives(controller_id=controller_id)

    @jsonize
    @dumb_error_handler
    def POST(self, controller_id):
        data = get_post_data()
        if 'drives' not in data:
            raise StorcliError(error_code=400,
                               msg='mandatory parameter "drives" is missing')
        web.ctx.status = '201 Created'
        param_names = ('raid_level', 'spare_drives', 'strip_size',
                       'name', 'read_ahead', 'write_cache', 'io_policy',
                       'ssd_caching')
        params = dict([(k, data.get(k)) for k in param_names])
        return self.storcli.create_virtual_drive(data['drives'], **params)

    @jsonize
    @dumb_error_handler
    def DELETE(self, controller_id):
        if controller_id != 'all':
            controller_id = int(controller_id)
        return get_storcli().\
            delete_virtual_drive(controller_id, 'all', force=True)


class CachecadeView(object):
    @jsonize
    @dumb_error_handler
    def GET(self, controller_id, raid_type):
        return get_storcli().virtual_drives(controller_id,
                                            raid_type=raid_type)

    @jsonize
    @dumb_error_handler
    def POST(self, controller_id, raid_type):
        data = get_post_data()
        if 'drives' not in data:
            raise StorcliError(error_code=400,
                               msg='mandatory parameter "drives" is missing')
        params = {'raid_level': data.get('raid_level', 0),
                  'raid_type': raid_type,
                  'name': data.get('name'),
                  'write_cache': data.get('write_cache'),
                  }
        web.ctx.status = '201 Created'
        return get_storcli().create_virtual_drive(data['drives'], **params)


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
        data = get_post_data()
        param_names = ('name', 'read_ahead', 'write_cache', 'io_policy',
                       'ssd_caching')
        params = dict([(k, data.get(k)) for k in param_names])
        return self.storcli.update_virtual_drive(int(controller_id),
                                                 int(virtual_drive_id),
                                                 **params)


class CachecadeDetails(object):
    @jsonize
    @dumb_error_handler
    def GET(self, controller_id, raid_type, virtual_drive_id):
        return get_storcli().\
            virtual_drive_details(controller_id, int(virtual_drive_id),
                                  raid_type=raid_type)

    @jsonize
    @dumb_error_handler
    def DELETE(self, controller_id, raid_type, virtual_drive_id):
        return get_storcli().\
            delete_virtual_drive(controller_id,
                                 virtual_drive_id,
                                 raid_type=raid_type)


class WarpdriveView(object):
    @jsonize
    @dumb_error_handler
    def POST(self, controller_id):
        try:
            data = json.loads(web.data())
            overprovision = data.get('overprovision')
        except:
            overprovision = None
        return get_storcli().\
            create_warp_drive_vd(controller_id,
                                 overprovision=overprovision)


class HotspareOps(object):
    @jsonize
    @dumb_error_handler
    def POST(self, controller_id, enclosure, slot):
        try:
            data = json.loads(web.data())
            virtual_drives = data.get('virtual_drives')
        except:
            virtual_drives = None

        return get_storcli().\
            add_hotspare_drive(virtual_drives,
                               controller_id=controller_id,
                               enclosure=enclosure,
                               slot=slot)

    @jsonize
    @dumb_error_handler
    def DELETE(self, controller_id, enclosure, slot):
        return get_storcli().\
            delete_hotspare_drive(controller_id=controller_id,
                                  enclosure=enclosure,
                                  slot=slot)

if __name__ == '__main__':
    app.run()
