#
# Copyright 2015-2017 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#


from __future__ import absolute_import
from __future__ import division
import errno

_RPFILTER_STRICT = '1'
_RPFILTER_LOOSE = '2'


def set_rp_filter(dev, mode):
    path = '/proc/sys/net/ipv4/conf/%s/rp_filter' % dev
    with open(path, 'w') as rp_filter:
        rp_filter.write(mode)


def set_rp_filter_loose(dev):
    set_rp_filter(dev, _RPFILTER_LOOSE)


def set_rp_filter_strict(dev):
    set_rp_filter(dev, _RPFILTER_STRICT)


def enable_ipv6(dev):
    disable_ipv6(dev, disable=False)


def disable_ipv6(dev, disable=True):
    with open('/proc/sys/net/ipv6/conf/%s/disable_ipv6' % dev, 'w') as f:
        f.write('1' if disable else '0')


def is_disabled_ipv6(dev='default'):
    with open('/proc/sys/net/ipv6/conf/%s/disable_ipv6' % dev) as f:
        return int(f.read())


def is_ipv6_local_auto(dev):
    try:
        is_disabled = is_disabled_ipv6(dev)
        with open('/proc/sys/net/ipv6/conf/%s/autoconf' % dev) as f:
            is_autoconf = int(f.read())
        with open('/proc/sys/net/ipv6/conf/%s/accept_ra' % dev) as f:
            is_accept_ra = int(f.read())
        with open('/proc/sys/net/ipv6/conf/%s/accept_redirects' % dev) as f:
            is_accept_redirects = int(f.read())
    except IOError as e:
        if e.errno == errno.ENOENT:
            return False
        else:
            raise

    return bool(not is_disabled and
                is_autoconf and is_accept_ra and is_accept_redirects)


def enable_ipv6_local_auto(dev):
    return _set_ipv6_local_auto(dev, True)


def disable_ipv6_local_auto(dev):
    return _set_ipv6_local_auto(dev, False)


def _set_ipv6_local_auto(dev, state):
    if is_disabled_ipv6(dev):
        if state:
            enable_ipv6(dev)
        else:
            return

    setstate = '1' if state else '0'
    with open('/proc/sys/net/ipv6/conf/%s/autoconf' % dev, 'w') as f:
        f.write(setstate)
    with open('/proc/sys/net/ipv6/conf/%s/accept_ra' % dev, 'w') as f:
        f.write(setstate)
    with open('/proc/sys/net/ipv6/conf/%s/accept_redirects' % dev, 'w') as f:
        f.write(setstate)
