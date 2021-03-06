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
import mock
import unittest

from tests_helpers import MultiReturnValues, add_top_srcdir_to_path,\
    read_expected


add_top_srcdir_to_path()

import storrest
from storrest.storutils import strlst, vd_raid_type

STORCLI_SHOW = read_expected('call_show.json')
STORCLI_SHOW_ALL = read_expected('call_show_all.json')
STORCLI_ENCLOSURES_SHOW = read_expected('c0_eall_show.json')
STORCLI_C0_EALL_SALL_SHOW = read_expected('c0_eall_sall_show_all.json')
STORCLI_C1_SALL_SHOW = read_expected('c1_sall_show_all.json')


def extract_controller_raw_data(raw_dat, controller_id, serialize=True):
    def _controller_match(ctrl):
        return ctrl['Command Status']['Controller'] == controller_id

    dat = json.loads(raw_dat)
    subdat = [ctrl for ctrl in dat['Controllers'] if _controller_match(ctrl)]
    ret = {'Controllers': subdat}
    return json.dumps(ret) if serialize else ret


class StorcliTest(unittest.TestCase):
    def setUp(self):
        super(StorcliTest, self).setUp()
        self.maxDiff = None
        self.patcher = mock.patch('storrest.storcli.subprocess.check_output')
        self.mock_check_output = self.patcher.start()
        self.mock_check_output.return_value = STORCLI_SHOW_ALL
        self.storcli = storrest.storcli.Storcli()
        self._expected_virtual_drives = None
        self._expected_physical_drives = None
        self._controller_details = None
        self.controllers = [{'controller_id': 0,
                             'pci_address': '00:06:00:00',
                             'model': 'Nytro MegaRAID8100-4i',
                             'serial_number': '',
                             'enclosures': [62, 252],
                             'host_interface': 'PCIE',
                             'sas_address': '5000000012345678',
                             'capabilities': {'max_cachecade_size': 1024, },
                             'health': None,
                             },
                            {'controller_id': 1,
                             'pci_address': None,
                             'model': "Nytro WarpDrive XP6210-4A2048",
                             'serial_number': '123456789',
                             'host_interface': 'PCIE',
                             'sas_address': ' 500605b012061206',
                             'enclosures': [],
                             'capabilities': {'max_cachecade_size': 0, },
                             'health': {
                                 'temperature': ' 72 (degree C)',
                                 'warranty_remaining': ' 100 (percent)',
                                 'overall_health': 'GOOD',
                             },
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
        self.mock_check_output.side_effect = MultiReturnValues([
            STORCLI_SHOW,
            STORCLI_C0_EALL_SALL_SHOW,
            STORCLI_C1_SALL_SHOW
        ])
        actual = sorted(self.storcli.all_physical_drives)
        expected_commands = (
            '{storcli_cmd} /call show J',
            '{storcli_cmd} /c0/eall/sall show all J',
            '{storcli_cmd} /c1/sall show all J',
        )
        self.verify_storcli_commands(expected_commands)
        self.assertEqual(actual, self.expected_physical_drives)

    def test_virtual_drives(self):
        self.mock_check_output.side_effect = MultiReturnValues([
            STORCLI_SHOW,
            STORCLI_C0_EALL_SALL_SHOW,
            STORCLI_C1_SALL_SHOW
        ])
        actual = sorted(self.storcli.all_virtual_drives)
        expected_commands = (
            '{storcli_cmd} /call show J',
            '{storcli_cmd} /c0/eall/sall show all J',
            '{storcli_cmd} /c1/sall show all J',
        )
        self.verify_storcli_commands(expected_commands)
        self.assertEqual(actual, self.expected_virtual_drives)

    def _get_nytrocache(self, raid_type='nytrocache'):
        self.mock_check_output.side_effect = MultiReturnValues([
            STORCLI_SHOW,
            STORCLI_C0_EALL_SALL_SHOW,
            STORCLI_C1_SALL_SHOW
        ])
        expected_commands = (
            '{storcli_cmd} /call show J',
            '{storcli_cmd} /c0/eall/sall show all J',
            '{storcli_cmd} /c1/sall show all J',
        )
        actual = sorted(self.storcli.virtual_drives(raid_type=raid_type))
        self.verify_storcli_commands(expected_commands)
        expected = sorted([vd for vd in self.expected_virtual_drives
                           if vd_raid_type(vd) == raid_type])
        self.assertEqual(actual, expected)

    def test_get_nytrocache(self):
        self._get_nytrocache(raid_type='nytrocache')

    def test_get_cachecade(self):
        self._get_nytrocache(raid_type='cachecade')

    def test_controllers(self):
        self.mock_check_output.side_effect = MultiReturnValues([
            STORCLI_SHOW_ALL,
            STORCLI_ENCLOSURES_SHOW,
            read_expected('c0_show_health.json'),
            read_expected('c1_show_health.json')
        ])
        actual = self.storcli.controllers
        self.assertEqual(actual, self.controllers)
        expected_commands = (
            '{storcli_cmd} /call show all J',
            # controller 1 is NytroWarpDrive and has no enclosures
            '{storcli_cmd} /c0/eall show J',
            '{storcli_cmd} /c0 show health J',
            '{storcli_cmd} /c1 show health J',
        )
        self.verify_storcli_commands(expected_commands)

    @property
    def controller_details(self):
        if self._controller_details is not None:
            return self._controller_details
        for cobj in self.controllers:
            cobj['physical_drives'] = \
                sorted([d for d in self.expected_physical_drives
                        if d['controller_id'] == cobj['controller_id']])
            cobj['virtual_drives'] = \
                sorted([vd for vd in self.expected_virtual_drives
                        if vd['controller_id'] == cobj['controller_id']])
        self._controller_details = self.controllers
        return self._controller_details

    def _test_controller_details(self, capabilities=True,
                                 controller_health_works=False):
        controller_id = 0
        controller_dat = extract_controller_raw_data(STORCLI_SHOW_ALL,
                                                     controller_id,
                                                     serialize=False)
        if not capabilities:
            del controller_dat['Controllers'][0][
                'Response Data']['Capabilities']

        controller_health = read_expected(
            'c{0}_show_health.json'.format(controller_id), raw=False)
        if controller_health_works:
            status_obj = controller_health['Controllers'][0]['Command Status']
            del status_obj['ErrCd']
            status_obj['Status'] = 'Success'
            expected_controller = [c for c in self.controllers
                                   if c['controller_id'] == controller_id][0]
            expected_controller['health'] = {
                'temperature': '74',
                'overall_health': 'GOOD',
                'warranty_remaining': '100',
            }

        self.mock_check_output.side_effect = MultiReturnValues([
            json.dumps(controller_dat),
            STORCLI_ENCLOSURES_SHOW,
            json.dumps(controller_health),
            STORCLI_C0_EALL_SALL_SHOW,
        ])
        expected = [c for c in self.controller_details
                    if c['controller_id'] == controller_id][0]
        if not capabilities:
            expected['capabilities']['max_cachecade_size'] = 0

        actual = self.storcli.controller_details(controller_id=controller_id)
        actual['physical_drives'] = sorted(actual['physical_drives'])
        actual['virtual_drives'] = sorted(actual['virtual_drives'])
        self.assertEqual(actual, expected)
        expected_commands = (
            '{storcli_cmd} /c{controller_id} show all J',
            '{storcli_cmd} /c{controller_id}/eall show J',
            '{storcli_cmd} /c{controller_id} show health J',
            '{storcli_cmd} /c{controller_id}/eall/sall show all J',
        )
        self.verify_storcli_commands(expected_commands,
                                     controller_id=controller_id)

    def test_controller_details(self):
        self._test_controller_details()

    def test_controller_details_nocaps(self):
        self._test_controller_details(capabilities=False)

    def test_controller_details_health(self):
        self._test_controller_details(controller_health_works=True)

    def test_controller_details_all(self):
        controller_id = None
        self.mock_check_output.side_effect = MultiReturnValues([
            STORCLI_SHOW_ALL,
            STORCLI_ENCLOSURES_SHOW,
            read_expected('c0_show_health.json'),
            STORCLI_C0_EALL_SALL_SHOW,
            read_expected('c1_show_health.json'),
            STORCLI_C1_SALL_SHOW,
        ])
        expected_commands = (
            '{storcli_cmd} /call show all J',
            '{storcli_cmd} /c0/eall show J',
            '{storcli_cmd} /c0 show health J',
            '{storcli_cmd} /c0/eall/sall show all J',
            '{storcli_cmd} /c1 show health J',
            '{storcli_cmd} /c1/sall show all J',
        )
        actual = self.storcli.controller_details(controller_id)
        self.verify_storcli_commands(expected_commands)
        self.assertEqual(actual, self.controller_details)

    def test_virtual_drive_details(self):
        controller_id = 0
        virtual_drive_id = 0
        self.mock_check_output.side_effect = MultiReturnValues([
            extract_controller_raw_data(STORCLI_SHOW_ALL, controller_id),
            STORCLI_C0_EALL_SALL_SHOW
        ])
        actual = self.storcli.virtual_drive_details(controller_id,
                                                    virtual_drive_id)
        expected = [vd for vd in self.expected_virtual_drives
                    if vd['controller_id'] == controller_id and
                    vd['virtual_drive'] == virtual_drive_id][0]
        expected_commands = (
            '{storcli_cmd} /c{controller_id} show J',
            '{storcli_cmd} /c{controller_id}/eall/sall show all J',
        )
        self.assertEqual(actual, expected)
        self.verify_storcli_commands(expected_commands,
                                     controller_id=controller_id)

    def test_virtual_drive_details_nonexistent(self):
        self.mock_check_output.return_value = STORCLI_SHOW
        controller_id = 0
        virtual_drive_id = 100500
        with self.assertRaises(storrest.storcli.StorcliError):
            self.storcli.virtual_drive_details(controller_id,
                                               virtual_drive_id)
        expected_commands = (
            '{storcli_cmd} /c{controller_id} show J',
            '{storcli_cmd} /c0/eall/sall show all J',
            '{storcli_cmd} /c1/sall show all J',
        )
        self.verify_storcli_commands(expected_commands,
                                     controller_id=controller_id)

    def verify_storcli_commands(self, expected_commands, **kwargs):
        kwargs['storcli_cmd'] = ' '.join(self.storcli.storcli_cmd)
        expected_calls = [((cmd.format(**kwargs).split(), ), {})
                          for cmd in expected_commands]
        actual_calls = self.mock_check_output.call_args_list
        self.assertEqual(actual_calls, expected_calls)

    def _make_success_reply(self, controller_id, serialize=True):
        return self._make_reply(controller_id, serialize=serialize)

    def _make_reply(self, controller_id, error_code=None, serialize=True):
        data = {
            'Controllers': [
                {
                    'Command Status': {
                        'Controller': controller_id,
                        'Status': 'Success' if not error_code else 'Failed',
                        'Description': 'None',
                    },
                },
            ]}

        if error_code:
            data['Controllers'][0]['Command Status']['ErrCd'] = error_code

        return json.dumps(data) if serialize else data

    def _mock_success_reply(self, controller_id):
        self.mock_check_output.return_value = \
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

        overprovision_level = 'overprovision level'
        try:
            testval = int(overprovision)
            overprovision_level = 'overprovision'
        except:
            pass

        expected_commands = (
            '{storcli_cmd} /c{controller_id}/eall/sall start format '
            '{overprovision_level}={overprovision} J',

        )
        self.verify_storcli_commands(expected_commands,
                                     controller_id=controller_id,
                                     overprovision_level=overprovision_level,
                                     overprovision=overprovision)

    def test_create_warp_drive_vd_cap(self):
        self._create_warp_drive_vd_overprovision('cap')

    def test_create_warp_drive_vd_perf(self):
        self._create_warp_drive_vd_overprovision('perf')

    def test_create_warp_drive_vd_percentage(self):
        self._create_warp_drive_vd_overprovision(50)

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
        pd_per_array = ''
        if raid_level in ('10', 10):
            pd_per_array = 2
        if pd_per_array:
            pd_per_array = 'PDperArray={0}'.format(pd_per_array)

        ssd_caching = raid_type is None
        io_policy = 'direct'

        self.mock_check_output.side_effect = MultiReturnValues([
            self._make_success_reply(controller_id),
            extract_controller_raw_data(STORCLI_SHOW, controller_id),
            STORCLI_C0_EALL_SALL_SHOW
        ])

        self.storcli.create_virtual_drive(physical_drives,
                                          raid_level=raid_level,
                                          raid_type=raid_type,
                                          io_policy=io_policy,
                                          ssd_caching=ssd_caching)
        expected_commands = (
            '{storcli_cmd} /c{controller_id} add vd {raid_type} '
            'r{raid_level} drives={drives_str} '
            '{pd_per_array} {io_policy} {ssd_caching} J',
            '{storcli_cmd} /c{controller_id} show J',
            '{storcli_cmd} /c{controller_id}/eall/sall show all J',
        )
        drives_str = '{enclosure}:{slots}'.format(enclosure=enclosure,
                                                  slots=strlst(slots))
        params = {
            'controller_id': controller_id,
            'raid_type': raid_type or '',
            'raid_level': raid_level,
            'drives_str': drives_str,
            'io_policy': io_policy,
            'ssd_caching': 'cachevd' if ssd_caching else '',
            'pd_per_array': pd_per_array,
        }
        self.verify_storcli_commands(expected_commands, **params)

    def test_create_raid1(self):
        self._create_raid()

    def test_create_nytrocache(self):
        self._create_raid(raid_type='nytrocache')

    def test_create_raid10(self):
        self._create_raid(raid_level=10)

    def _create_raid_negative(self, valid_reply=True):
        raid_level = 1
        controller_id = 0
        enclosure = 62
        slots = (0, 1)
        physical_drives = [{
            'controller_id': controller_id,
            'enclosure': enclosure,
            'slot': slot
        } for slot in slots]
        self.mock_check_output.return_value = \
            self._make_reply(controller_id, error_code=42) \
            if valid_reply else 'choke; JSON! parser'
        expected_commands = (
            '{storcli_cmd} /c{controller_id} add vd '
            'r{raid_level} drives={enclosure}:{slots_str} J',
        )
        with self.assertRaises(storrest.storcli.StorcliError) as cm:
            self.storcli.create_virtual_drive(physical_drives,
                                              raid_level=raid_level)
        the_exception = cm.exception
        if not valid_reply:
            self.assertEqual(the_exception.error_code,
                             storrest.storcli.INVALID_NYTROCLI_JSON)
        self.verify_storcli_commands(expected_commands,
                                     controller_id=controller_id,
                                     enclosure=enclosure,
                                     slots_str=strlst(slots),
                                     raid_level=raid_level)

    def test_create_virtual_drive_negative(self):
        self._create_raid_negative()

    def test_create_virtual_drive_invalid_reply(self):
        self._create_raid_negative(valid_reply=False)

    def test_create_virtual_drive_enclosure_missing(self):
        raid_level = 1
        controller_id = 0
        slots = (0, 1)
        physical_drives = [{
            'controller_id': controller_id,
            # no enclosure here, this is intensional
            'slot': slot
        } for slot in slots]
        with self.assertRaises(storrest.storcli.StorcliError):
            self.storcli.create_virtual_drive(physical_drives,
                                              raid_level=raid_level)
        self.verify_storcli_commands([])

    def test_delete_virtual_drive(self):
        controller_id = 0
        virtual_drive_id = 1
        force = True
        self._mock_success_reply(controller_id)
        expected_commands = (
            '{storcli_cmd} /c{controller_id}/v{virtual_drive_id} del {force} J',
        )
        self.storcli.delete_virtual_drive(controller_id,
                                          virtual_drive_id,
                                          force=force)
        self.verify_storcli_commands(expected_commands,
                                     controller_id=controller_id,
                                     virtual_drive_id=virtual_drive_id,
                                     force='force' if force else '')

    def _delete_all(self, controller_id=None, is_warpdrive=False):
        self.mock_check_output.side_effect = MultiReturnValues([
            STORCLI_SHOW_ALL,
            self._make_success_reply(controller_id)
        ])
        vdrives_id = '0' if is_warpdrive else 'all'
        expected_commands = (
            '{storcli_cmd} /c{controller_id} show all J',
            '{storcli_cmd} /c{controller_id}/v%s del J' % vdrives_id,
        )
        self.storcli.delete_virtual_drive(controller_id, 'all')
        self.verify_storcli_commands(expected_commands,
                                     controller_id=controller_id)

    def test_delete_warpdrive(self):
        self._delete_all(controller_id=1, is_warpdrive=True)

    def test_delete_all_virtual_drives(self):
        self._delete_all(controller_id=0, is_warpdrive=False)

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

    def test_global_hotspare_create_pdrive(self):
        pdrive = {
            'controller_id': 0,
            'enclosure': 62,
            'slot': 19
        }
        self._mock_success_reply(pdrive['controller_id'])
        expected_commands = (
            '{storcli_cmd} /c{controller_id}/e{enclosure}/s{slot} '
            'add hotsparedrive J',
        )
        self.storcli.add_hotspare_drive(None, pdrive=pdrive)
        self.verify_storcli_commands(expected_commands, **pdrive)

    def test_add_dedicated_hotspare(self):
        params = {
            'controller_id': 0,
            'enclosure': 62,
            'slot': 19,
        }
        target_vd = [vd for vd in self.expected_virtual_drives
                     if vd['controller_id'] == params['controller_id'] and
                     not vd['raid_level'].startswith('Nytro')][0]
        vdrives = [target_vd['virtual_drive']]

        self.mock_check_output.side_effect = MultiReturnValues([
            extract_controller_raw_data(STORCLI_SHOW,
                                        controller_id=params['controller_id']),
            STORCLI_C0_EALL_SALL_SHOW,
            self._make_success_reply(params['controller_id'])
        ])
        self.storcli.add_hotspare_drive(vdrives, **params)
        expected_commands = (
            '{storcli_cmd} /c{controller_id} show J',
            '{storcli_cmd} /c{controller_id}/eall/sall show all J',
            '{storcli_cmd} /c{controller_id}/e{enclosure}/s{slot} add '
            'hotsparedrive dgs={drive_group} J',
        )
        params['drive_group'] = target_vd['drive_group']
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

    def test_nonexisting_command(self):
        self.mock_check_output.side_effect = \
            OSError(2, 'no such file or directory', '/foo')
        cli = storrest.storcli.Storcli(storcli_cmd=['/foo'])
        with self.assertRaises(storrest.storcli.StorcliError):
            cli.all_virtual_drives

    def test_faulty_command(self):
        controller_id = 1
        returncode = 111
        error_code = 42
        command_output = self._make_reply(controller_id, error_code=error_code)
        self.mock_check_output.side_effect = \
            storrest.storcli.subprocess.CalledProcessError(
                returncode,
                self.storcli.storcli_cmd,
                output=command_output
            )
        with self.assertRaises(storrest.storcli.StorcliError) as ee:
            self.storcli.all_virtual_drives
        the_exception = ee.exception
        self.assertEqual(the_exception.error_code, error_code)


class StorutilsTest(unittest.TestCase):
    def test_parse_phys_drive_state_unusual(self):
        from storrest.storutils import parse_phys_drive_state
        raw_weird_state = 'FooBar'
        processed_weird_state = parse_phys_drive_state(raw_weird_state)
        self.assertEqual(raw_weird_state.lower(), processed_weird_state)

    def test_size_units_conversion(self):
        from storrest.storutils import parse_drive_size
        sizes_tbl = {
            '1 Mb': 1024 * 1024,
            '10 Kb': 10 * 1024,
            '2 Tb': 2 * 1024 * 1024 * 1024 * 1024,
        }
        for str_size, size in sizes_tbl.iteritems():
            self.assertEqual(parse_drive_size(str_size), size)

    def test_size_units_conversion_negative(self):
        from storrest.storutils import parse_drive_size
        with self.assertRaises(ValueError):
            parse_drive_size('100500 FooBar')

    def test_parse_weird_virtual_drive_state(self):
        from storrest.storutils import parse_state
        raw_weird_state = 'FooBar'
        weird_state = parse_state(raw_weird_state)
        self.assertEqual(weird_state, raw_weird_state.lower())

    def test_vd_raid_type(self):
        from storrest.storutils import vd_raid_type
        self.assertEqual(vd_raid_type({'raid_level': 'CacheCade1'}),
                         'cachecade')
        self.assertEqual(vd_raid_type({'raid_level': 'NytroCache1'}),
                         'nytrocache')

    def test_parse_sector_size(self):
        from storrest.storutils import parse_sector_size
        self.assertEqual(parse_sector_size('512B'), 512)
        self.assertEqual(parse_sector_size('4Kb'), 4096)
        with self.assertRaises(ValueError):
            parse_sector_size('foo bar')

    def test_parse_cache_flags_negative(self):
        from storrest.storutils import parse_cache_flags

        with self.assertRaises(ValueError):
            parse_cache_flags('foo bar')

        with self.assertRaises(ValueError):
            parse_cache_flags('NRWTF')


if __name__ == '__main__':
    unittest.main()
