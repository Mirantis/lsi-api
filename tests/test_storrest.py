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



if __name__ == '__main__':
    unittest.main()
