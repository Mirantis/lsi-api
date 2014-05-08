#!/usr/bin/env python

import mock
import subprocess
import unittest

import tests_helpers

tests_helpers.add_top_srcdir_to_path()

from storrest.storcli import Storcli

STORCLI_SHOW_JSON = """
{
"Controllers":[
{
    "Command Status" : {
        "Controller" : 0,
        "Status" : "Success",
        "Description" : "None"
    },
    "Response Data" : {
        "Product Name" : "LSI MegaRAID SAS 9260-4i",
        "Serial Number" : "SV24603934",
        "SAS Address" : " 500605b00594e5e0",
        "PCI Address" : "00:06:00:00",
        "System Time" : "05/07/2014 16:04:39",
        "Mfg. Date" : "11/10/12",
        "Controller Time" : "05/07/2014 16:04:38",
        "FW Package Build" : "12.12.0-0139",
        "FW Version" : "2.130.373-2022",
        "BIOS Version" : "3.26.00_4.12.05.00_0x05210000",
        "Driver Name" : "megaraid_sas",
        "Driver Version" : "06.506.00.00-rc1",
        "Vendor Id" : 4096,
        "Device Id" : 121,
        "SubVendor Id" : 4096,
        "SubDevice Id" : 37472,
        "Host Interface" : "PCIE",
        "Device Interface" : "SAS-6G",
        "Bus Number" : 6,
        "Device Number" : 0,
        "Function Number" : 0,
        "Drive Groups" : 1,
        "TOPOLOGY" : [
            {
                "DG" : 0,
                "Arr" : "-",
                "Row" : "-",
                "EID:Slot" : "-",
                "DID" : "-",
                "Type" : "RAID1",
                "State" : "Optl",
                "BT" : "N",
                "Size" : "931.0 GB",
                "PDC" : "dflt",
                "PI" : "N",
                "SED" : "N",
                "DS3" : "none",
                "FSpace" : "N"
            },
            {
                "DG" : 0,
                "Arr" : 0,
                "Row" : "-",
                "EID:Slot" : "-",
                "DID" : "-",
                "Type" : "RAID1",
                "State" : "Optl",
                "BT" : "N",
                "Size" : "931.0 GB",
                "PDC" : "dflt",
                "PI" : "N",
                "SED" : "N",
                "DS3" : "none",
                "FSpace" : "N"
            },
            {
                "DG" : 0,
                "Arr" : 0,
                "Row" : 0,
                "EID:Slot" : "252:0",
                "DID" : 5,
                "Type" : "DRIVE",
                "State" : "Onln",
                "BT" : "N",
                "Size" : "931.0 GB",
                "PDC" : "dflt",
                "PI" : "N",
                "SED" : "N",
                "DS3" : "none",
                "FSpace" : "-"
            },
            {
                "DG" : 0,
                "Arr" : 0,
                "Row" : 1,
                "EID:Slot" : "252:1",
                "DID" : 6,
                "Type" : "DRIVE",
                "State" : "Onln",
                "BT" : "N",
                "Size" : "931.0 GB",
                "PDC" : "dflt",
                "PI" : "N",
                "SED" : "N",
                "DS3" : "none",
                "FSpace" : "-"
            },
            {
                "DG" : 0,
                "Arr" : "-",
                "Row" : "-",
                "EID:Slot" : "252:2",
                "DID" : 7,
                "Type" : "DRIVE",
                "State" : "DHS",
                "BT" : "-",
                "Size" : "931.0 GB",
                "PDC" : "-",
                "PI" : "-",
                "SED" : "-",
                "DS3" : "-",
                "FSpace" : "-"
            }
        ],
        "Virtual Drives" : 1,
        "VD LIST" : [
            {
                "DG/VD" : "0/0",
                "TYPE" : "RAID1",
                "State" : "Optl",
                "Access" : "RW",
                "Consist" : "No",
                "Cache" : "RWBD",
                "sCC" : "-",
                "Size" : "931.0 GB",
                "Name" : "test_raid1"
            }
        ],
        "Physical Drives" : 4,
        "PD LIST" : [
            {
                "EID:Slt" : "252:0",
                "DID" : 5,
                "State" : "Onln",
                "DG" : 0,
                "Size" : "931.0 GB",
                "Intf" : "SATA",
                "Med" : "HDD",
                "SED" : "N",
                "PI" : "N",
                "SeSz" : "512B",
                "Model" : "ST1000NM0011",
                "Sp" : "U"
            },
            {
                "EID:Slt" : "252:1",
                "DID" : 6,
                "State" : "Onln",
                "DG" : 0,
                "Size" : "931.0 GB",
                "Intf" : "SATA",
                "Med" : "HDD",
                "SED" : "N",
                "PI" : "N",
                "SeSz" : "512B",
                "Model" : "ST1000NM0011",
                "Sp" : "U"
            },
            {
                "EID:Slt" : "252:2",
                "DID" : 7,
                "State" : "DHS",
                "DG" : "0",
                "Size" : "931.0 GB",
                "Intf" : "SATA",
                "Med" : "HDD",
                "SED" : "N",
                "PI" : "N",
                "SeSz" : "512B",
                "Model" : "ST1000NM0011",
                "Sp" : "D"
            },
            {
                "EID:Slt" : "252:3",
                "DID" : 4,
                "State" : "UGood",
                "DG" : "-",
                "Size" : "931.0 GB",
                "Intf" : "SATA",
                "Med" : "HDD",
                "SED" : "N",
                "PI" : "N",
                "SeSz" : "512B",
                "Model" : "ST1000NM0011",
                "Sp" : "D"
            }
        ],
        "BBU_Info" : [
            {
                "Model" : "iBBU",
                "State" : "Optimal",
                "RetentionTime" : "48 hours +",
                "Temp" : "24C",
                "Mode" : "-",
                "MfgDate" : "2012/09/22",
                "Next Learn" : "2014/05/09  18:14:01"
            }
        ]
    }
}
]
}
"""


class StorcliTest(unittest.TestCase):
    def setUp(self):
        super(StorcliTest, self).setUp()
        subprocess.check_output = mock.Mock(return_value=STORCLI_SHOW_JSON)
        self.storcli = Storcli()
        self._expected_virtual_drives = None
        self._expected_physical_drives = None
        self.controllers = [{'controller_id': 0,
                             'pci_address': '00:06:00:00',
                             'model': 'LSI MegaRAID SAS 9260-4i',
                             'serial_number': 'SV24603934'}]

    @property
    def expected_physical_drives(self):
        if self._expected_physical_drives:
            return self._expected_physical_drives
        else:
            physical_drives = [{'controller_id': 0,
                                'enclosure': 252,
                                'slot': 0,
                                'size': 999653638144,
                                'sector_size': 512,
                                'drive_group': 0,
                                'model': 'ST1000NM0011',
                                'state': 'online',
                                'allocated': True},
                               {'controller_id': 0,
                                'enclosure': 252,
                                'slot': 1,
                                'size': 999653638144,
                                'sector_size': 512,
                                'drive_group': 0,
                                'model': 'ST1000NM0011',
                                'state': 'online',
                                'allocated': True},
                               {'controller_id': 0,
                                'enclosure': 252,
                                'slot': 2,
                                'size': 999653638144,
                                'sector_size': 512,
                                'drive_group': 0,
                                'model': 'ST1000NM0011',
                                'state': 'dedicated_hot_spare',
                                'allocated': True},
                               {'controller_id': 0,
                                'enclosure': 252,
                                'slot': 3,
                                'size': 999653638144,
                                'sector_size': 512,
                                'drive_group': None,
                                'model': 'ST1000NM0011',
                                'state': 'unconfigured_good',
                                'allocated': False}]
            physical_drives.sort()
            self._expected_physical_drives = physical_drives
            return self._expected_physical_drives

    @property
    def expected_virtual_drives(self):
        if self._expected_virtual_drives:
            return self._expected_virtual_drives
        else:
            vds = [{'controller_id': 0,
                    'virtual_drive': 0,
                    'drive_group': 0,
                    'size': 999653638144,
                    'state': 'optimal',
                    'raid_level': '1',
                    'name': 'test_raid1',
                    'access': 'rw',
                    'consistent': False,
                    'read_ahead': True,
                    'write_cache': 'wb',
                    'io_policy': 'direct'}]
            drive_group = vds[0]['drive_group']
            physical_drives = [d for d in self.expected_physical_drives
                               if d['drive_group'] == drive_group]
            vds[0]['physical_drives'] = sorted(physical_drives)
            self._expected_virtual_drives = vds
            return self._expected_virtual_drives

    def test_physical_drives(self):
        actual = self.storcli.all_physical_drives
        self.assertEqual(actual, self.expected_physical_drives)

    def test_virtual_drives(self):
        actual = self.storcli.all_virtual_drives
        self.assertEqual(actual, self.expected_virtual_drives)

    def test_controllers(self):
        actual = self.storcli.controllers
        self.assertEqual(actual, self.controllers)

    def test_controller_details(self):
        expected = self.controllers[0]
        expected['physical_drives'] = self.expected_physical_drives
        expected['virtual_drives'] = self.expected_virtual_drives
        actual = self.storcli.controller_details(
            controller_id=expected['controller_id'])
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
