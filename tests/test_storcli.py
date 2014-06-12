#!/usr/bin/env python

import mock
import unittest

from tests_helpers import MultiReturnValues, add_top_srcdir_to_path,\
    read_expected


add_top_srcdir_to_path()

import storrest

STORCLI_SHOW = read_expected('call_show.json')
STORCLI_SHOW_ALL = read_expected('call_show_all.json')
STORCLI_ENCLOSURES_SHOW = read_expected('c0_eall_show.json')


class StorcliTest(unittest.TestCase):
    def setUp(self):
        super(StorcliTest, self).setUp()
        self.maxDiff = None
        self.patcher = mock.patch('storrest.storcli.subprocess')
        self.mock_subprocess = self.patcher.start()
        self.mock_subprocess.check_output.return_value = STORCLI_SHOW
        self.storcli = storrest.storcli.Storcli()
        self._expected_virtual_drives = None
        self._expected_physical_drives = None
        self.controllers = [{'controller_id': 0,
                             'pci_address': '00:06:00:00',
                             'model': 'Nytro MegaRAID8100-4i',
                             'serial_number': '',
                             'enclosures': [62, 252],
                             },
                            {'controller_id': 1,
                             'pci_address': None,
                             'model': "Nytro WarpDrive XP6210-4A2048",
                             'serial_number': '123456789',
                             'enclosures': [],
                             }]

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

    def test_virtual_drives(self):
        actual = sorted(self.storcli.all_virtual_drives)
        self.assertEqual(actual, self.expected_virtual_drives)

    def test_controllers(self):
        self.mock_subprocess.check_output.side_effect = MultiReturnValues([
            STORCLI_SHOW_ALL, STORCLI_ENCLOSURES_SHOW])
        actual = self.storcli.controllers
        self.assertEqual(actual, self.controllers)

    def test_controller_details(self):
        self.mock_subprocess.check_output.side_effect = MultiReturnValues([
            STORCLI_SHOW_ALL, STORCLI_ENCLOSURES_SHOW])
        expected = self.controllers[0]
        controller_id = expected['controller_id']
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


if __name__ == '__main__':
    unittest.main()
