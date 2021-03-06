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
import logging
import subprocess

import storutils
from storcli_health import HealthInfoParser
from storutils import *

if 'check_output' not in dir(subprocess):
    from storcompat import patch_subprocess
    patch_subprocess(subprocess)

STORCLI_CMD = '/opt/MegaRAID/nytrocli/nytrocli64'.split()
SOMETHING_BAD_HAPPEND = 42
NO_SUCH_VDRIVE = SOMETHING_BAD_HAPPEND
INVALID_NYTROCLI_JSON = 100500
MULTIPLE_VDS_FOR_SAME_PDS = SOMETHING_BAD_HAPPEND
LOG = logging.getLogger('storrest.storcli')


class StorcliError(Exception):
    def __init__(self, msg, error_code=None):
        super(StorcliError, self).__init__(msg)
        self.error_code = error_code


class Storcli(object):
    def __init__(self, storcli_cmd=STORCLI_CMD):
        self.storcli_cmd = storcli_cmd
        self._health_parser = HealthInfoParser()

    def _extract_storcli_data(self, data, error_code=None):
        ret = {}
        for controller_out in data['Controllers']:
            status_obj = controller_out['Command Status']
            controller_id = status_obj['Controller']
            status = status_obj['Status']
            if status != 'Success':
                LOG.info('error data: %s', data)
                error_code = status_obj.get('ErrCd', SOMETHING_BAD_HAPPEND)
                raise StorcliError(status_obj.get('Description', 'Unknown'),
                                   error_code=error_code)
            ret[controller_id] = controller_out.get('Response Data', {})
        return ret

    def _run(self, cmd, permissive=False):
        _cmd = []
        _cmd.extend(self.storcli_cmd)
        _cmd.extend(cmd)
        _cmd.append('J')
        error_code = None
        try:
            raw_out = subprocess.check_output(_cmd)
        except subprocess.CalledProcessError, e:
            raw_out = e.output
            error_code = e.returncode
        except OSError, oe:
            msg = 'Failed to run "{cmd}", error: {errno} ({strerror})'
            msg = msg.format(cmd=' '.join(_cmd),
                             errno=oe.errno,
                             strerror=oe.strerror)
            raise StorcliError(msg, error_code=oe.errno)

        def skip_nytrocli_debug_messages(s):
            paren_idx = s.find('{')
            return s[paren_idx:] if paren_idx != -1 else s

        if permissive:
            raw_out = skip_nytrocli_debug_messages(raw_out)

        try:
            out = json.loads(raw_out)
        except:
            LOG.info('invalid JSON %s', raw_out)
            raise StorcliError(msg='invalid JSON received',
                               error_code=INVALID_NYTROCLI_JSON)
        out = self._extract_storcli_data(out, error_code)
        return out

    def _parse_controller_data(self, controller_id, dat):
        def get_host_interface(obj):
            # XXX: for some reason this information is located
            # in different subobjects for WarpDrive and MegaRAID.
            key = 'Host Interface'
            bus_dat = obj.get('Bus')
            if bus_dat:
                return bus_dat.get(key)
            version_dat = obj.get('Version')
            if version_dat:
                return version_dat.get(key)

        cinf = {'controller_id': controller_id,
                'pci_address': dat['Basics'].get('PCI Address'),
                'model': dat['Basics'].get('Model'),
                'serial_number': dat['Basics'].get('Serial Number'),
                'sas_address': dat['Basics'].get('SAS Address'),
                'host_interface': get_host_interface(dat),
                }
        # XXX: nytrocli errors out when trying to enumerate the enclosures
        # of Nytro WarpDrive (instead of givin an empty list)
        if cinf['model'].startswith('Nytro WarpDrive'):
            enclosures = []
        else:
            enclosures = self._enclosures(controller_id)
        cinf['enclosures'] = enclosures
        cinf['capabilities'] = self._controller_capabilities(dat)
        cinf['health'] = self._controller_health(controller_id)
        return cinf

    def _enclosures(self, controller_id):
        dat = self._run('/c{0}/eall show'.format(controller_id).split())
        return sorted([d['EID'] for d in dat[controller_id]['Properties']])

    @property
    def controllers(self):
        data = self._run('/call show all'.split())
        return sorted([self._parse_controller_data(controller_id, dat)
                       for controller_id, dat in data.iteritems()])

    def _controller_capabilities(self, dat):
        caps = dat.get('Capabilities')
        if not caps:
            return {'max_cachecade_size': 0, }
        max_cachecade_size = caps.get('Max Configurable CacheCade Size', 0)
        return {'max_cachecade_size': max_cachecade_size, }

    def _parse_controller_health(self, cdat):
        megaraid_tbl = {
            'temperature': 'TemperatureROC',
            'overall_health': 'Overall Health',
            'warranty_remaining': 'Warranty Remaining'
        }
        nwd_tbl = {
            'temperature': 'Temperature',
            'overall_health': 'Overall Health',
            'warranty_remaining': 'Warranty Remaining'
        }

        is_nwd = (len(cdat.keys()) == 1) and cdat.keys()[0].endswith('Health')
        if is_nwd:
            tbl = nwd_tbl
            health = cdat[cdat.keys()[0]].get('Controller Health')
        else:
            tbl = megaraid_tbl
            health = cdat.get('Controller Health Info')

        return dict([(key, str(health.get(mangled_key)))
                     for key, mangled_key in tbl.iteritems()])

    def _controller_health(self, controller_id):
        cmd = '/c{0} show health'.format(controller_id)
        try:
            data = self._run(cmd.split(), permissive=True)
        except StorcliError:
            return None
        return self._parse_controller_health(data[controller_id])

    def controller_details(self, controller_id):
        if controller_id is None:
            controller_id = 'all'
        cmd = '/c{0} show all'.format(controller_id)
        data = self._run(cmd.split())

        def _controller_details(cid, dat):
            details = self._parse_controller_data(cid, dat)
            _dat = {cid: dat}
            physical_drives = self._parse_physical_drives(_dat)
            details['virtual_drives'] = self._parse_virtual_drives(
                _dat,
                phys_drives=physical_drives
            )
            details['physical_drives'] = physical_drives
            return details

        ret = [_controller_details(_controller_id, dat)
               for _controller_id, dat in data.iteritems()]
        all_controllers = controller_id is None or controller_id == 'all'
        return sorted(ret) if all_controllers else ret[0]

    def _parse_physical_drive(self, controller, drive_dat):
        enclosure, slot = drive_dat['EID:Slt'].split(':')
        enclosure = int(enclosure) if enclosure.strip() != '' else None

        def parse_drive_group(raw_dg):
            allocated = raw_dg != '-'
            drive_group = None
            if allocated:
                try:
                    drive_group = int(raw_dg)
                except ValueError:
                    try:
                        drive_group = [int(dg) for dg in raw_dg.split(',')]
                    except ValueError:
                        drive_group = raw_dg
            return drive_group, allocated

        drive_group, allocated = parse_drive_group(drive_dat['DG'])
        sector_size = storutils.parse_sector_size(drive_dat['SeSz'])
        size = storutils.parse_drive_size(drive_dat['Size'])
        return {'controller_id': controller,
                'enclosure': enclosure,
                'slot': int(slot),
                'drive_group': drive_group,
                'size': size,
                'sector_size': sector_size,
                'allocated': allocated,
                'state': storutils.parse_phys_drive_state(drive_dat['State']),
                'medium': drive_dat.get('Med'),
                'interface': drive_dat.get('Intf'),
                'model': drive_dat['Model']}

    def _get_raw_health_info(self, controller_id, is_warpdrive):
        health_cmd = '/c{0}/eall/sall show all'
        if is_warpdrive:
            health_cmd = '/c{0}/sall show all'
        health_cmd = health_cmd.format(controller_id)
        return self._run(health_cmd.split())

    def _add_health_info(self, controller_id, pdrives, is_warpdrive=False):
        raw_health_info = self._get_raw_health_info(controller_id,
                                                    is_warpdrive)
        self._health_parser.add_health_info(controller_id,
                                            raw_health_info,
                                            pdrives)

    def _parse_physical_drives(self, data):
        ret = []
        for controller_id, controller_data in data.iteritems():
            is_warpdrive = self._is_warpdrive(controller_id,
                                              controller_data=controller_data)
            drives = [self._parse_physical_drive(controller_id, drive_dat)
                      for drive_dat in controller_data.get('PD LIST', [])]
            self._add_health_info(controller_id, drives, is_warpdrive)
            ret.extend(drives)
        return sorted(ret)

    def physical_drives(self, controller_id=None):
        if controller_id is None:
            controller_id = 'all'
        cmd = '/c{0} show'.format(controller_id)
        data = self._run(cmd.split())
        return self._parse_physical_drives(data)

    def _parse_virtual_drive(self, controller, vdrive_dat):
        try:
            drive_group, virtual_drive = vdrive_dat['DG/VD'].split('/')
        except AttributeError:
            # XXX: sometimes nytrocli puts an integer here
            if isinstance(vdrive_dat['DG/VD'], int):
                drive_group = virtual_drive = vdrive_dat['DG/VD']
            else:
                raise
        size = storutils.parse_drive_size(vdrive_dat['Size'])
        raid_level = storutils.parse_raid_level(vdrive_dat['TYPE'])
        consistent = vdrive_dat['Consist'].lower() == 'yes'
        read_ahead, write_cache, io_policy = \
                storutils.parse_cache_flags(vdrive_dat['Cache'])
        state = storutils.parse_state(vdrive_dat['State'])

        def _ssd_caching_active(vdrive_dat):
            val = vdrive_dat.get('Cac')
            if val is None or val == '-':
                return None
            else:
                return val.lower()

        return {'controller_id': controller,
                'virtual_drive': int(virtual_drive),
                'drive_group': int(drive_group),
                'state': state,
                'size': size,
                'raid_level': raid_level,
                'access': vdrive_dat['Access'].lower(),
                'name': vdrive_dat['Name'],
                'consistent': consistent,
                'read_ahead': read_ahead,
                'write_cache': write_cache,
                'io_policy': io_policy,
                'ssd_caching_active': _ssd_caching_active(vdrive_dat),
                }

    def _parse_virtual_drives(self, data, phys_drives=None):

        def drive_belongs_to(phys, virt):
            if phys['drive_group'] is None:
                return False
            if phys['controller_id'] != virt['controller_id']:
                return False
            if phys['drive_group'] == virt['drive_group']:
                return True
            try:
                return virt['drive_group'] in phys['drive_group']
            except TypeError:
                return False

        if phys_drives is None:
            phys_drives = self._parse_physical_drives(data)

        def find_physical_drives_of_vdrive(vdrive):
            pdrives = [d for d in phys_drives if drive_belongs_to(d, vdrive)]
            pdrives.sort()
            vdrive['physical_drives'] = pdrives

        ret = []
        for controller, response_data in data.iteritems():
            vdrives = [self._parse_virtual_drive(controller, vdrive_dat)
                       for vdrive_dat in response_data.get('VD LIST', [])]
            map(find_physical_drives_of_vdrive, vdrives)
            ret.extend(vdrives)
        return sorted(ret)

    def virtual_drive_details(self, controller_id, virtual_drive_id,
                              raid_type=None):
        vdrives = [d for d in self.virtual_drives(controller_id=controller_id)
                   if d['virtual_drive'] == virtual_drive_id and raid_type ==
                   vd_raid_type(d)]
        try:
            return vdrives[0]
        except IndexError:
            msg = 'No such virtual drive /c{0}/v{1}'
            raise StorcliError(msg.format(controller_id, virtual_drive_id),
                               error_code=NO_SUCH_VDRIVE)

    def virtual_drives(self, controller_id=None, raid_type=None):
        if controller_id is None:
            controller_id = 'all'
        cmd = '/c{0} show'.format(controller_id)
        vds = self._parse_virtual_drives(self._run(cmd.split()))
        raid_type = self._validate_raid_type(raid_type)
        if raid_type:
            vds = [vd for vd in vds if vd_raid_type(vd) == raid_type]
        return sorted(vds)

    def _is_warpdrive(self, controller_id, controller_data=None):
        if controller_data is None:
            cmd = '/c{0} show all'.format(controller_id)
            data = self._run(cmd.split())
            controller_data = data[controller_id]
        if 'Basics' in controller_data:
            model = controller_data['Basics']['Model']
        elif 'Product Name' in controller_data:
            model = controller_data['Product Name']
        return model.startswith('Nytro WarpDrive')

    def delete_virtual_drive(self, controller_id, virtual_drive_id,
                             force=False, raid_type=None):
        cmd = '/c{controller_id}/v{virtual_drive_id} del {raid_type} {force}'
        raid_type = self._validate_raid_type(raid_type)
        if raid_type:
            # force doesn't seem to work with cachecade/nytrocache
            force = False

        # work around nytrocli bug
        if virtual_drive_id == 'all' and self._is_warpdrive(controller_id):
            virtual_drive_id = 0

        cmd = cmd.format(controller_id=controller_id,
                         virtual_drive_id=virtual_drive_id,
                         raid_type='cc' if raid_type else '',
                         force='force' if force else '')
        return self._run(cmd.split())

    def _find_virtual_drive_by_phisical(self, physical_drives):
        def physical_drives_ids(drives):
            return set([(pd['enclosure'], pd['slot']) for pd in drives])

        controller_id = physical_drives[0]['controller_id']
        pdrives_ids = physical_drives_ids(physical_drives)
        found_vd = [vd for vd in self.virtual_drives(controller_id)
                    if physical_drives_ids(vd['physical_drives']) ==
                    pdrives_ids]
        if len(found_vd) == 1:
            return found_vd[0]
        elif len(found_vd) == 0:
            msg = 'No virtual drive contains %s'
            error_code = NO_SUCH_VDRIVE
        elif len(found_vd) > 1:
            msg = 'Multiple virtual drives contain %s'
            error_code = MULTIPLE_VDS_FOR_SAME_PDS
        raise StorcliError(msg % pdrives_ids, error_code=error_code)

    def _validate_raid_type(self, raid_type):
        funky_raid_types = ['cachecade', 'nytrocache']
        return raid_type if raid_type in funky_raid_types else ''

    def _validate_physical_drives(self, pdrives):
        try:
            return [{'controller_id': int(pd['controller_id']),
                     'enclosure': int(pd['enclosure']),
                     'slot': int(pd['slot'])}
                    for pd in pdrives]
        except:
            raise StorcliError(error_code=SOMETHING_BAD_HAPPEND,
                               msg='Invalid physical drives specified')

    def create_virtual_drive(self, physical_drives,
                             spare_drives=None,
                             raid_level=0,
                             strip_size=None,
                             ssd_caching=None,
                             name=None,
                             read_ahead=None,
                             write_cache=None,
                             io_policy=None,
                             raid_type=None):
        def fmt_drives_info(drives):
            enclosure = drives[0]['enclosure']
            slots = ','.join(['%(slot)s' % d for d in drives])
            return '%s:%s' % (enclosure, slots)

        def guess_pd_per_array(raid_level, cmd):
            tbl = {'10': 2, 10: 2,
                   '50': 3, 50: 3,
                   '60': 4, 60: 4}
            if raid_level in tbl:
                cmd.append('PDperArray=%s' % tbl[raid_level])

        raid_type = self._validate_raid_type(raid_type)
        physical_drives = self._validate_physical_drives(physical_drives)

        cmd = '/c{controller} add vd {raid_type} r{raid_level} {name} drives={drives}'
        params = {'controller': physical_drives[0]['controller_id'],
                  'raid_level': raid_level,
                  'drives': fmt_drives_info(physical_drives),
                  'name': 'name=%s' % name if name else '',
                  'raid_type': raid_type,
                  }
        cmd = cmd.format(**params).split()
        guess_pd_per_array(raid_level, cmd)
        if strip_size:
            cmd.append('Strip=%s' % strip_size)
        if read_ahead is not None:
            cmd.append('ra' if read_ahead else 'nora')
        if write_cache and write_cache in ['wb', 'wt']:
            cmd.append(write_cache)
        if io_policy and io_policy in ['direct', 'cached']:
            cmd.append(io_policy)
        if spare_drives:
            cmd.append('Spares=%s' % fmt_drives_info(spare_drives))
        if ssd_caching:
            cmd.append('cachevd')

        self._run(cmd)
        return self._find_virtual_drive_by_phisical(physical_drives +
                                                    (spare_drives or []))

    def update_virtual_drive(self, controller_id, virtual_drive_id,
                             name=None,
                             write_cache=None,
                             io_policy=None,
                             read_ahead=None,
                             ssd_caching=None):
        cmd = '/c{0}/v{1} set'.format(controller_id, virtual_drive_id).split()
        if io_policy in ['direct', 'cached']:
            cmd.append('iopolicy=%s' % io_policy)
        if name is not None:
            cmd.append('name=%s' % name)
        if write_cache in ['wb', 'wt']:
            cmd.append('wrcache=%s' % write_cache)
        if read_ahead is not None:
            cmd.append('rdcache=%s' % ('RA' if read_ahead else 'NoRA'))
        if ssd_caching is not None:
            cmd.append('ssdcaching=%s' % ('on' if ssd_caching else 'off'))

        return self._run(cmd)

    def add_hotspare_drive(self, virtual_drives,
                           pdrive=None,
                           controller_id=None,
                           enclosure=None,
                           slot=None):
        """Assign the physical drive as a hot spare for the virtual drives.

        pdrive the physical drive description. Example:
        {'controller_id': 0, 'enclosure': 252, 'slot': 1}

        virtual_drives list of virtual drives IDs
        """
        if pdrive is None:
            pdrive = {'controller_id': controller_id,
                      'enclosure': enclosure,
                      'slot': slot}
        else:
            controller_id = pdrive['controller_id']
        cmd = '/c{controller_id}/e{enclosure}/s{slot} add hotsparedrive'
        cmd = cmd.format(**pdrive).split()
        if virtual_drives:
            drive_groups = [vd['drive_group'] for vd in
                            self.virtual_drives(controller_id)
                            if vd['virtual_drive'] in virtual_drives]
            cmd.append('dgs=%s' % strlst(drive_groups))
        return self._run(cmd)

    def delete_hotspare_drive(self, drive=None,
                              controller_id=None,
                              enclosure=None,
                              slot=None):
        if drive is None:
            drive = {'controller_id': controller_id,
                     'enclosure': enclosure,
                     'slot': slot}
        cmd = '/c{controller_id}/e{enclosure}/s{slot} delete hotsparedrive'
        cmd = cmd.format(**drive)
        return self._run(cmd.split())

    def create_warp_drive_vd(self, controller_id, overprovision=None):
        cmd = '/c{0}/eall/sall start format'.format(controller_id).split()
        possible_levels = ('nom', 'cap', 'perf')
        if overprovision in possible_levels:
            cmd.extend('overprovision level={0}'.format(overprovision).split())
        else:
            overprovision = validate_percentage(overprovision)
            if overprovision is not None:
                cmd.append('overprovision=%s' % overprovision)
        return self._run(cmd, permissive=True)

    #physical_drives=property(_physical_drives)
    @property
    def all_physical_drives(self):
        return self.physical_drives()

    @property
    def all_virtual_drives(self):
        return self.virtual_drives()
