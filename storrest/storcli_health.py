
import re


class HealthInfoParser(object):
    def __init__(self):
        self._detailed_info_rx = re.compile('^Drive\s+/c(?P<controller_id>\d+)(/e(?P<enclosure>\d+))?/s(?P<slot>\d+)\s+[-]\s+Detailed\s+Information\s*$')
        self._state_rx = re.compile('^Drive\s+/c(?P<controller_id>\d+)(/e(?P<enclosure>\d+))/s(?P<slot>\d+)\s+State\s*$')

    def _drive_state_key(self, drive_addr_dict):
        # Something like 'Drive /c0/s32/s2 State'
        drive_addr_fmt = '/c{controller_id}/e{enclosure}/s{slot}'
        if drive_addr_dict.get('enclosure') is None:
            drive_addr_fmt = '/c{controller_id}/s{slot}'
        tpl = 'Drive {0} State'.format(drive_addr_fmt)
        return tpl.format(**drive_addr_dict)

    def _health_info(self, drive_addr_dict, drive_state):
        params_dict = {
            'temperature': 'Drive Temperature',
            'ssd_life_left': 'SSD Life Left',
        }
        health_info = {}
        for key, mangled_key in params_dict.iteritems():
            val = drive_state.get(mangled_key) if drive_state else None
            health_info[key] = val
        return health_info

    def _parse_drive_addr(self, dict_str):
        enclosure_str = dict_str.get('enclosure')
        if enclosure_str is None:
            enclosure = None
        else:
            enclosure = int(enclosure_str)
        return {
            'controller_id': int(dict_str['controller_id']),
            'enclosure': enclosure,
            'slot': int(dict_str['slot']),
        }

    def _drive_addr_tuple(self, drive_addr_dict):
        return (
            drive_addr_dict['controller_id'],
            drive_addr_dict['enclosure'],
            drive_addr_dict['slot'],
        )

    def drives_health(self, controller_id, dat):
        ret = {}
        for key, val in dat.iteritems():
            match = self._detailed_info_rx.match(key)
            if match is None:
                continue

            drive_addr_str = match.groupdict()
            drive_addr_dict = self._parse_drive_addr(drive_addr_str)
            drive_state_key = self._drive_state_key(drive_addr_dict)
            drive_state_info = val.get(drive_state_key)
            drive_addr_tuple = self._drive_addr_tuple(drive_addr_dict)
            ret[drive_addr_tuple] = self._health_info(drive_addr_dict,
                                                      drive_state_info)
        return ret

    def add_health_info(self, controller_id, raw_health_info, pdrives):
        health_info = self.drives_health(controller_id,
                                         raw_health_info[controller_id])
        for pd in pdrives:
            if controller_id != pd['controller_id']:
                continue
            pd_addr_tuple = self._drive_addr_tuple(pd)
            pd['health'] = health_info.get(pd_addr_tuple)
