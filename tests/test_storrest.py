#!/usr/bin/env python

import json
import mock
import unittest

from tests_helpers import add_top_srcdir_to_path

add_top_srcdir_to_path()

import storrest
import storrest.storcli
import storrest.storrest


class StorrestTest(unittest.TestCase):
    api_version = 'v0.5'
    dummy_data = {'foo': 'bar'}

    def setUp(self):
        super(StorrestTest, self).setUp()
        self.app = storrest.storrest.app

    def verify_reply(self, request):
        reply = json.loads(request.data)
        self.assertEqual(reply['data'], self.dummy_data)

    @mock.patch.object(storrest.storcli.Storcli, 'controller_details')
    def test_controllers(self, mock_obj):
        mock_obj.return_value = self.dummy_data
        controller_id = '0'
        request = self.app.request('/{0}/controllers/{1}'.
                                   format(self.api_version, controller_id))
        mock_obj.assert_called_once_with(controller_id)
        self.verify_reply(request)

    @mock.patch.object(storrest.storcli.Storcli, 'physical_drives')
    def test_physical_drives(self, mock_obj):
        mock_obj.return_value = self.dummy_data
        controller_id = '0'
        request = self.app.request('/{0}/controllers/{1}/physicaldevices'.
                                   format(self.api_version, controller_id))
        mock_obj.assert_called_once_with(controller_id=controller_id)
        self.verify_reply(request)

    @mock.patch.object(storrest.storcli.Storcli, 'virtual_drives')
    def test_virtual_drives(self, mock_obj):
        mock_obj.return_value = self.dummy_data
        controller_id = '0'
        request = self.app.request('/{0}/controllers/{1}/virtualdevices'.
                                   format(self.api_version, controller_id))
        mock_obj.assert_called_once_with(controller_id=controller_id)
        self.verify_reply(request)

    @mock.patch.object(storrest.storcli.Storcli, 'virtual_drive_details')
    def test_virtual_drive_details(self, mock_obj):
        mock_obj.return_value = self.dummy_data
        controller_id = 0
        virtual_drive_id = 0
        url = '/{0}/controllers/{1}/virtualdevices/{2}'.format(
            self.api_version,
            controller_id,
            virtual_drive_id)
        request = self.app.request(url)
        self.verify_reply(request)
        mock_obj.assert_called_once_with(controller_id, virtual_drive_id)

    @mock.patch.object(storrest.storcli.Storcli, 'create_virtual_drive')
    def test_create_virtual_drive(self, mock_obj):
        mock_obj.return_value = self.dummy_data
        controller_id = 0
        url = '/{0}/controllers/{1}/virtualdevices'.format(
            self.api_version,
            controller_id)
        data = {
            'drives': [{'controller_id': 0, 'enclosure': 4, 'slot': 0},
                       {'controller_id': 0, 'enclosure': 4, 'slot': 1}],
            'raid_level': '1',
            'name': 'test_r1'
        }
        request = self.app.request(url, method='POST', data=json.dumps(data))
        self.verify_reply(request)
        param_names = ('raid_level', 'spare_drives', 'strip_size',
                       'name', 'read_ahead', 'write_cache', 'io_policy',
                       'ssd_caching')
        params = dict([(k, data.get(k)) for k in param_names])
        mock_obj.assert_called_once_with(data['drives'], **params)

    @mock.patch.object(storrest.storcli.Storcli, 'delete_virtual_drive')
    def test_delete_virtual_drive(self, mock_obj):
        mock_obj.return_value = self.dummy_data
        controller_id = 0
        virtual_drive_id = 0
        url = '/{0}/controllers/{1}/virtualdevices/{2}'.format(
            self.api_version,
            controller_id,
            virtual_drive_id)
        request = self.app.request(url, method='DELETE')
        self.verify_reply(request)
        mock_obj.assert_called_once_with(str(controller_id),
                                         str(virtual_drive_id),
                                         force=True)

    @mock.patch.object(storrest.storcli.Storcli, 'update_virtual_drive')
    def test_update_virtual_drive(self, mock_obj):
        mock_obj.return_value = self.dummy_data
        controller_id = 0
        virtual_drive_id = 0
        url = '/{0}/controllers/{1}/virtualdevices/{2}'.format(
            self.api_version,
            controller_id,
            virtual_drive_id)
        data = {
            'name': 'foo',
            'read_ahead': True,
            'write_cache': 'wb',
            'io_policy': 'direct',
            'ssd_caching': True
        }
        request = self.app.request(url, method='POST', data=json.dumps(data))
        self.verify_reply(request)
        mock_obj.assert_called_once_with(controller_id,
                                         virtual_drive_id,
                                         **data)

    def _hotspare_url(self, controller_id=None, enclosure=None, slot=None):
        url = '/{0}/controllers/{controller_id}/physicaldevices' \
            '/{enclosure}/{slot}/hotspare'
        return url.format(self.api_version,
                          controller_id=controller_id,
                          enclosure=enclosure,
                          slot=slot)

    def _add_hotspare_test(self, mock_obj, virtual_drives=None):
        mock_obj.return_value = self.dummy_data
        controller_id = 0
        enclosure = 42
        slot = 100500
        data = {'virtual_drives': virtual_drives}
        data_json = json.dumps(data) if virtual_drives else None
        url = self._hotspare_url(controller_id, enclosure, slot)
        request = self.app.request(url, method='POST', data=data_json)
        self.verify_reply(request)
        mock_obj.assert_called_once_with(virtual_drives,
                                         controller_id=str(controller_id),
                                         enclosure=str(enclosure),
                                         slot=str(slot))

    @mock.patch.object(storrest.storcli.Storcli, 'add_hotspare_drive')
    def test_add_global_hotspare_drive(self, mock_obj):
        self._add_hotspare_test(mock_obj)

    @mock.patch.object(storrest.storcli.Storcli, 'add_hotspare_drive')
    def test_add_dedicated_hotspare_drive(self, mock_obj):
        self._add_hotspare_test(mock_obj, virtual_drives=[1, 2, 3])

    @mock.patch.object(storrest.storcli.Storcli, 'delete_hotspare_drive')
    def test_delete_hotspare_drive(self, mock_obj):
        mock_obj.return_value = self.dummy_data
        controller_id = 0
        enclosure = 42
        slot = 100500
        url = self._hotspare_url(controller_id, enclosure, slot)
        request = self.app.request(url, method='DELETE')
        self.verify_reply(request)
        mock_obj.assert_called_once_with(controller_id=str(controller_id),
                                         enclosure=str(enclosure),
                                         slot=str(slot))


if __name__ == '__main__':
    unittest.main()
