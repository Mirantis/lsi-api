
import re


def size_in_bytes(size, units):
    if units.upper() == 'GB':
        return int(size * 1024 * 1024 * 1024)
    elif units.upper() == 'TB':
        return int(size * 1024 * 1024 * 1024 * 1024)
    elif units.upper() == 'MB':
        return int(size * 1024 * 1024)
    elif units.upper() == 'KB':
        return int(size * 1024)
    else:
        raise ValueError('Unknown size units: %s' % units)


def parse_phys_drive_state(state_str):
    states = {'DHS': 'dedicated_hot_spare',
              'UGood': 'unconfigured_good',
              'GHS': 'global_hot_spare',
              'UBad': 'unconfigured_bad',
              'Onln': 'online',
              'Offln': 'offline'}
    if state_str in states:
        return states[state_str]
    else:
        raise ValueError('Unknown state: %s' % state_str)


def parse_drive_size(srep):
    size, units = srep.split()
    return size_in_bytes(float(size), units)


def parse_sector_size(srep):
    rx = re.compile('([1-9][0-9]*)(.*)')
    matched = rx.match(srep)
    if not matched:
        raise ValueError('Invalid sector size: %s' % srep)
    value, units = matched.groups()
    value = int(value)
    if units.upper() == 'B' or units == '':
        pass
    elif units.upper() == 'KB':
        value = value * 1024
    return value


def parse_raid_level(srep):
    level_str = srep.strip().upper()
    raid_levels = {'RAID1': '1',
                   'RAID0': '0',
                   'RAID5': '5',
                   'RAID6': '6',
                   'RAID10': '10',
                   'RAID50': '50',
                   'RAID60': '60',
                   }
    return raid_levels.get(level_str, srep)


def parse_cache_flags(flags):
    rx = re.compile('(n*r)(w[bt])([cd])')
    matched = rx.match(flags.strip().lower())
    if not matched:
        raise ValueError('Invalid cache flags: %s' % flags)
    if len(matched.groups()) != 3:
        raise ValueError('Invalid cache flags: %s' % flags)
    read_ahead, write_cache, io_policy = matched.groups()
    read_ahead = read_ahead == 'r'
    io_policy = 'direct' if io_policy == 'd' else 'cached'
    return (read_ahead, write_cache, io_policy)


def vd_raid_type(vd):
    raid_level = vd['raid_level'].lower()
    if raid_level.startswith('nytro'):
        return 'nytrocache'
    elif raid_level.startswith('cache'):
        return 'cachecade'
    else:
        return None


def parse_state(arg):
    smap = {'Optl': 'optimal',
            'OfLn': 'offline',
            'Pdgd': 'partially_degraded',
            'dgrd': 'degraded'}
    state_str = arg.strip()
    if state_str in smap:
        return smap[state_str]
    else:
        raise ValueError('Invalid state: %s' % arg)


def strlst(lst, separator=','):
    return separator.join((str(elt) for elt in lst))


def validate_integer(val, interval):
    try:
        v = int(val)
        val = v if interval[0] <= v <= interval[1] else None
    except (ValueError, TypeError):
        val = None
    return val


def validate_percentage(val):
    return validate_integer(val, (0, 100))
