#!/usr/bin/env python

from collections import defaultdict
import json
import subprocess

import storutils

STORCLI_CMD = '/opt/MegaRAID/storcli/storcli64'.split()
SOMETHING_BAD_HAPPEND = 42
NO_SUCH_VDRIVE = SOMETHING_BAD_HAPPEND


class StorcliError(Exception):
    def __init__(self, msg, controller_id=None):
        super(self, StorcliError).__init__(msg)
        self.controller_id = controller_id




class Storcli(object):
    def __init__(self, storcli_cmd=STORCLI_CMD):
        self.storcli_cmd = storcli_cmd

    def _extract_storcli_data(self, data):
        ret = {}
        for controller_out in data['Controllers']:
            status_obj = controller_out['Command Status']
            controller_id = status_obj['Controller']
            status = status_obj['Status']
            if status != 'Success':
                print '_extract_storcli_data: data: %s' % data
                raise StorcliError(status_obj.get('Description', 'Unknown'),
                                   controller_id=controller_id)
            ret[controller_id] = controller_out.get('Response Data', {})
            return ret

    def _run(self, cmd):
        _cmd = []
        _cmd.extend(self.storcli_cmd)
        _cmd.extend(cmd)
        _cmd.append('J')
        raw_out = subprocess.check_output(_cmd)
        out = json.loads(raw_out)
        out = self._extract_storcli_data(out)
        return out

    def _parse_controller_data(self, controller_id, dat):
        return {'controller_id': controller_id,
                'pci_address': dat['PCI Address'],
                'model': dat['Product Name'],
                'serial_number': dat['Serial Number']}

    @property
    def controllers(self):
        data = self._run('/call show'.split())
        return sorted([self._parse_controller_data(controller_id, dat)
                       for controller_id, dat in data.iteritems()])

    def controller_details(self, controller_id):
        data = self._run('/c{0} show'.format(controller_id).split())
        controller_id = data.keys()[0]
        details = self._parse_controller_data(controller_id,
                                              data[controller_id])
        details['physical_drives'] = self._parse_physical_drives(data)
        details['virtual_drives'] = self._parse_virtual_drives(data)
        return details

    def _parse_physical_drive(self, controller, drive_dat):
        enclosure, slot = drive_dat['EID:Slt'].split(':')
        allocated = drive_dat['DG'] != '-'
        drive_group = int(drive_dat['DG']) if allocated else None
        sector_size = storutils.parse_sector_size(drive_dat['SeSz'])
        size = storutils.parse_drive_size(drive_dat['Size'])
        return {'controller_id': controller,
                'enclosure': int(enclosure),
                'slot': int(slot),
                'drive_group': drive_group,
                'size': size,
                'sector_size': sector_size,
                'allocated': allocated,
                'state': storutils.parse_phys_drive_state(drive_dat['State']),
                'model': drive_dat['Model']}

    def _parse_physical_drives(self, data):
        ret = []
        for controller, response_data in data.iteritems():
            drives = [self._parse_physical_drive(controller, drive_dat)
                      for drive_dat in response_data.get('PD LIST', [])]
            ret.extend(drives)
        return sorted(ret)

    def physical_drives(self, controller=None):
        controller = controller or 'all'
        cmd = '/c%s show' % controller
        data = self._run(cmd.split())
        return self._parse_physical_drives(data)

    def _parse_virtual_drive(self, controller, vdrive_dat):
        drive_group, virtual_drive = vdrive_dat['DG/VD'].split('/')
        size = storutils.parse_drive_size(vdrive_dat['Size'])
        raid_level = storutils.parse_raid_level(vdrive_dat['TYPE'])
        consistent = vdrive_dat['Consist'].lower() == 'yes'
        read_ahead, write_cache, io_policy = \
                storutils.parse_cache_flags(vdrive_dat['Cache'])
        state = storutils.parse_state(vdrive_dat['State'])
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
                }

    def _parse_virtual_drives(self, data):
        def physical_drives_by_group(phys_drives):
            ret = defaultdict(list)
            for pd in phys_drives:
                ret[pd['drive_group']].append(pd)
            return ret

        def drive_belongs_to(phys, virt):
            return virt['drive_group'] == phys['drive_group'] and \
                    virt['controller_id'] == phys['controller_id']

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

    def virtual_drive_details(self, controller_id, virtual_drive_id):
        vdrives = [d for d in self.virtual_drives(controller_id=controller_id)
                   if d['virtual_drive'] == virtual_drive_id]
        try:
            return vdrives[0]
        except IndexError:
            msg = 'No such virtual drive /c{0}/v{1}'
            raise StorcliError(msg.format(controller_id, virtual_drive_id),
                               error_code=NO_SUCH_VDRIVE)

    def virtual_drives(self, controller_id=None):
        cmd = '/c{0} show'.format(controller_id or 'all')
        return self._parse_virtual_drives(self._run(cmd.split()))

    def delete_virtual_drive(self, controller_id, virtual_drive_id,
                             force=False):
        cmd = '/c%s/v%s del' % (controller_id, virtual_drive_id)
        cmd = cmd.split()
        if force:
            cmd.append('force')
        data = self._run(cmd)
        return data


    #physical_drives=property(_physical_drives)
    @property
    def all_physical_drives(self):
        return self.physical_drives()

    @property
    def all_virtual_drives(self):
        return self.virtual_drives()
