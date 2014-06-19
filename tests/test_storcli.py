#!/usr/bin/env python

import json
import mock
import unittest

from tests_helpers import MultiReturnValues, add_top_srcdir_to_path,\
    read_expected


add_top_srcdir_to_path()

import storrest
from storrest.storutils import strlst

STORCLI_SHOW = read_expected('call_show.json')
STORCLI_SHOW_ALL = read_expected('call_show_all.json')
STORCLI_ENCLOSURES_SHOW = read_expected('c0_eall_show.json')


class StorcliTest(unittest.TestCase):
    def setUp(self):
        super(StorcliTest, self).setUp()
        self.maxDiff = None
        self.patcher = mock.patch('storrest.storcli.subprocess')
        self.mock_subprocess = self.patcher.start()
        self.mock_subprocess.check_output.return_value = STORCLI_SHOW_ALL
        self.storcli = storrest.storcli.Storcli()
        self._expected_virtual_drives = None
        self._expected_physical_drives = None
        self.controllers = [{'controller_id': 0,
                             'pci_address': '00:06:00:00',
                             'model': 'Nytro MegaRAID8100-4i',
                             'serial_number': '',
                             'enclosures': [62, 252],
                             'capabilities': {'max_cachecade_size': 1024, },
                             },
                            {'controller_id': 1,
                             'pci_address': None,
                             'model': "Nytro WarpDrive XP6210-4A2048",
                             'serial_number': '123456789',
                             'enclosures': [],
                             'capabilities': {'max_cachecade_size': 0, },
                             }]
        self.controllers = sorted(self.controllers)

    def tearDown(self):
        super(StorcliTest, self).tearDown()
        self.patcher.stop()

    @property
    def expected_physical_drives(self):
        if self._expected_physical_drives:
            return self._expected_physical_drives
        else:
            physical_drives = read_expected('pdrives.json', raw=False)
            self._expected_physical_drives = sorted(physical_drives)
            return self._expected_physical_drives

    @property
    def expected_virtual_drives(self):
        if self._expected_virtual_drives:
            return self._expected_virtual_drives
        else:
            vds = read_expected('vdrives_skel.json', raw=False)
            for vd in vds:
                drive_group = vd['drive_group']
                controller_id = vd['controller_id']
                pdrives = sorted([d for d in self.expected_physical_drives
                                  if d['controller_id'] == controller_id
                                  and d['drive_group'] == drive_group])
                vd['physical_drives'] = pdrives
            self._expected_virtual_drives = sorted(vds)
            return self._expected_virtual_drives

    def test_physical_drives(self):
        actual = sorted(self.storcli.all_physical_drives)
        self.assertEqual(actual, self.expected_physical_drives)
        self.verify_storcli_commands(('{storcli_cmd} /call show J',))

    def test_virtual_drives(self):
        actual = sorted(self.storcli.all_virtual_drives)
        self.assertEqual(actual, self.expected_virtual_drives)
        self.verify_storcli_commands(('{storcli_cmd} /call show J',))

    def test_controllers(self):
        self.mock_subprocess.check_output.side_effect = MultiReturnValues([
            STORCLI_SHOW_ALL, STORCLI_ENCLOSURES_SHOW])
        actual = self.storcli.controllers
        self.assertEqual(actual, self.controllers)
        expected_commands = (
            '{storcli_cmd} /call show all J',
            # controller 1 is NytroWarpDrive and has no enclosures
            '{storcli_cmd} /c0/eall show J'
        )
        self.verify_storcli_commands(expected_commands)

    def test_controller_details(self):
        self.mock_subprocess.check_output.side_effect = MultiReturnValues([
            STORCLI_SHOW_ALL, STORCLI_ENCLOSURES_SHOW])
        controller_id = 0
        expected = [c for c in self.controllers
                    if c['controller_id'] == controller_id][0]
        expected['physical_drives'] = \
            sorted([d for d in self.expected_physical_drives
                    if d['controller_id'] == controller_id])
        expected['virtual_drives'] = \
            sorted([vd for vd in self.expected_virtual_drives
                    if vd['controller_id'] == controller_id])

        actual = self.storcli.controller_details(controller_id=controller_id)
        actual['physical_drives'] = sorted(actual['physical_drives'])
        actual['virtual_drives'] = sorted(actual['virtual_drives'])
        self.assertEqual(actual, expected)
        expected_commands = (
            '{storcli_cmd} /c{controller_id} show all J',
            '{storcli_cmd} /c{controller_id}/eall show J'
        )
        self.verify_storcli_commands(expected_commands,
                                     controller_id=controller_id)

    def verify_storcli_commands(self, expected_commands, **kwargs):
        kwargs['storcli_cmd'] = ' '.join(self.storcli.storcli_cmd)
        expected_calls = [((cmd.format(**kwargs).split(), ), {})
                          for cmd in expected_commands]
        actual_calls = self.mock_subprocess.check_output.call_args_list
        self.assertEqual(actual_calls, expected_calls)

    def _make_success_reply(self, controller_id, serialize=True):
        data = {
            'Controllers': [
                {
                    'Command Status': {
                        'Controller': controller_id,
                        'Status': 'Success',
                        'Description': 'None',
                    },
                },
            ]}
        return json.dumps(data) if serialize else data

    def _mock_success_reply(self, controller_id):
        self.mock_subprocess.check_output.return_value = \
            self._make_success_reply(controller_id)

    def test_create_warp_drive_vd_dflt(self):
        controller_id = 0
        self._mock_success_reply(controller_id)
        self.storcli.create_warp_drive_vd(controller_id)
        expected_commands = (
            '{storcli_cmd} /c{controller_id}/eall/sall start format J',
        )
        self.verify_storcli_commands(expected_commands,
                                     controller_id=controller_id)

    def _create_warp_drive_vd_overprovision(self, overprovision):
        controller_id = 0
        self._mock_success_reply(controller_id)
        self.storcli.create_warp_drive_vd(controller_id,
                                          overprovision=overprovision)
        expected_commands = (
            '{storcli_cmd} /c{controller_id}/eall/sall start format overprovision level={overprovision} J',
        )
        self.verify_storcli_commands(expected_commands,
                                     controller_id=controller_id,
                                     overprovision=overprovision)

    def test_create_warp_drive_vd_cap(self):
        self._create_warp_drive_vd_overprovision('cap')

    def test_create_warp_drive_vd_perf(self):
        self._create_warp_drive_vd_overprovision('perf')

    def _create_raid(self,
                     raid_type=None,
                     raid_level=1):
        # XXX: these values must correspond the controllers state in
        # call_show_all.json (i.e. drives on specified controller, enclosure
        # and slots are part of RAID1 array)
        controller_id = 0
        if raid_type is None:
            enclosure = 62
            slots = (0, 1)
        elif raid_type == 'nytrocache':
            enclosure = '252'
            slots = ('4', 6)

        physical_drives = [{
            'controller_id': controller_id,
            'enclosure': enclosure,
            'slot': slot
        } for slot in slots]
        self.mock_subprocess.check_output.side_effect = MultiReturnValues([
            self._make_success_reply(controller_id),
            STORCLI_SHOW])

        self.storcli.create_virtual_drive(physical_drives,
                                          raid_level=raid_level,
                                          raid_type=raid_type)
        expected_commands = (
            '{storcli_cmd} /c{controller_id} add vd {raid_type} '
            'r{raid_level} drives={drives_str} J',
            '{storcli_cmd} /c{controller_id} show J'
        )
        drives_str = '{enclosure}:{slots}'.format(enclosure=enclosure,
                                                  slots=strlst(slots))
        self.verify_storcli_commands(expected_commands,
                                     controller_id=controller_id,
                                     raid_type=raid_type or '',
                                     raid_level=raid_level,
                                     drives_str=drives_str)

    def test_create_raid1(self):
        self._create_raid()

    def test_create_nytrocache(self):
        self._create_raid(raid_type='nytrocache')

    def test_global_hotspare_create(self):
        params = {
            'controller_id': 0,
            'enclosure': 62,
            'slot': 19
        }
        self._mock_success_reply(params['controller_id'])
        self.storcli.add_hotspare_drive(None, **params)
        expected_commands = (
            '{storcli_cmd} /c{controller_id}/e{enclosure}/s{slot} '
            'add hotsparedrive J',
        )
        self.verify_storcli_commands(expected_commands, **params)

    def test_hotspare_delete(self):
        params = {
            'controller_id': 0,
            'enclosure': 62,
            'slot': 19
        }
        self._mock_success_reply(params['controller_id'])
        self.storcli.delete_hotspare_drive(**params)
        expected_commands = (
            '{storcli_cmd} /c{controller_id}/e{enclosure}/s{slot} '
            'delete hotsparedrive J',
        )
        self.verify_storcli_commands(expected_commands, **params)

    def test_update_virtual_drive(self):
        controller_id = 0
        virtual_drive_id = 1
        self._mock_success_reply(controller_id)
        params = {
            'name': 'FooBar',
            'io_policy': 'direct',
            'write_cache': 'wb',
            'read_ahead': False,
            'ssd_caching': True,
        }
        self.storcli.update_virtual_drive(controller_id,
                                          virtual_drive_id,
                                          **params)
        expected_commands = (
            '{storcli_cmd} /c{controller_id}/v{virtual_drive_id} set '
            'iopolicy={io_policy} name={name} wrcache={write_cache} '
            'rdcache={read_ahead} ssdcaching={ssd_caching} J',
        )
        params['controller_id'] = controller_id
        params['virtual_drive_id'] = virtual_drive_id
        params['ssd_caching'] = 'on' if params['ssd_caching'] else 'off'
        params['read_ahead'] = 'RA' if params['read_ahead'] else 'NoRA'
        self.verify_storcli_commands(expected_commands, **params)


if __name__ == '__main__':
    unittest.main()
