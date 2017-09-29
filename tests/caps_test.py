#
# Copyright 2012-2017 Red Hat, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301  USA
#
# Refer to the README and COPYING files for full details of the license
#

import os
import platform
import tempfile
import xml.etree.ElementTree as ET
from testlib import VdsmTestCase as TestCaseBase
from monkeypatch import MonkeyPatch

from vdsm.host import caps
from vdsm import commands
from vdsm import cpuarch
from vdsm import numa
from vdsm import machinetype
from vdsm import osinfo
from vdsm.common import cache


def _getTestData(testFileName):
    testPath = os.path.realpath(__file__)
    dirName = os.path.dirname(testPath)
    path = os.path.join(dirName, testFileName)
    with open(path) as src:
        return src.read()


def _getCapsNumaDistanceTestData(testFileName):
    return (0, _getTestData(testFileName).splitlines(False), [])


class TestCaps(TestCaseBase):

    CPU_MAP_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                'cpu_map.xml')

    def tearDown(self):
        for name in dir(caps):
            obj = getattr(caps, name)
            if isinstance(obj, cache.memoized):
                obj.invalidate()

    def _readCaps(self, fileName):
        testPath = os.path.realpath(__file__)
        dirName = os.path.split(testPath)[0]
        path = os.path.join(dirName, fileName)
        with open(path) as f:
            return f.read()

    @MonkeyPatch(numa, 'memory_by_cell', lambda x: {
        'total': '1', 'free': '1'})
    @MonkeyPatch(platform, 'machine', lambda: cpuarch.PPC64)
    def testCpuTopologyPPC64(self):
        testPath = os.path.realpath(__file__)
        dirName = os.path.split(testPath)[0]
        # PPC64 4 sockets, 5 cores, 1 threads per core
        path = os.path.join(dirName, "caps_libvirt_ibm_S822L.out")
        t = numa.cpu_topology(open(path).read())
        self.assertEqual(t.threads, 20)
        self.assertEqual(t.cores, 20)
        self.assertEqual(t.sockets, 4)

    @MonkeyPatch(numa, 'memory_by_cell', lambda x: {
        'total': '1', 'free': '1'})
    @MonkeyPatch(platform, 'machine', lambda: cpuarch.S390X)
    def testCpuTopologyS390X(self):
        testPath = os.path.realpath(__file__)
        dirName = os.path.split(testPath)[0]
        # S390 1 socket, 4 cores, 1 threads per core
        path = os.path.join(dirName, "caps_libvirt_s390x.out")
        t = numa.cpu_topology(open(path).read())
        self.assertEqual(t.threads, 4)
        self.assertEqual(t.cores, 4)
        self.assertEqual(t.sockets, 1)

    @MonkeyPatch(numa, 'memory_by_cell', lambda x: {
        'total': '1', 'free': '1'})
    @MonkeyPatch(platform, 'machine', lambda: cpuarch.X86_64)
    def testCpuTopologyX86_64(self):
        testPath = os.path.realpath(__file__)
        dirName = os.path.split(testPath)[0]
        # 2 x Intel E5649 (with Hyperthreading)
        path = os.path.join(dirName, "caps_libvirt_intel_E5649.out")
        with open(path) as p:
            t = numa.cpu_topology(p.read())
        self.assertEqual(t.threads, 24)
        self.assertEqual(t.cores, 12)
        self.assertEqual(t.sockets, 2)
        # 2 x AMD 6272 (with Modules)
        path = os.path.join(dirName, "caps_libvirt_amd_6274.out")
        with open(path) as p:
            t = numa.cpu_topology(p.read())
        self.assertEqual(t.threads, 32)
        self.assertEqual(t.cores, 16)
        self.assertEqual(t.sockets, 2)
        # 1 x Intel E31220 (normal Multi-core)
        path = os.path.join(dirName, "caps_libvirt_intel_E31220.out")
        with open(path) as p:
            t = numa.cpu_topology(p.read())
        self.assertEqual(t.threads, 4)
        self.assertEqual(t.cores, 4)
        self.assertEqual(t.sockets, 1)

    def testEmulatedMachines(self):
        capsData = self._readCaps("caps_libvirt_amd_6274.out")
        machines = set(machinetype.emulated_machines(cpuarch.X86_64,
                                                     capsData))
        expectedMachines = {'pc-1.0', 'pc', 'isapc', 'pc-0.12', 'pc-0.13',
                            'pc-0.10', 'pc-0.11', 'pc-0.14', 'pc-0.15'}
        self.assertEqual(machines, expectedMachines)

    def test_parseKeyVal(self):
        lines = ["x=&2", "y& = 2", " z = 2 ", " s=3=&'5", " w=", "4&"]
        expectedRes = [{'x': '&2', 'y&': '2', 'z': '2', 's': "3=&'5", 'w': ''},
                       {'x=': '2', 'y': '= 2', 's=3=': "'5", '4': ''}]
        sign = ["=", "&"]
        for res, s in zip(expectedRes, sign):
            self.assertEqual(res, caps._parseKeyVal(lines, s))

    def test_parse_node_version(self):
        inputs = (b'',
                  b'VERSION = 1\n',
                  b'RELEASE = 2\n',
                  b'VERSION = 1\nRELEASE = 2\n',
                  b'VERSIO = 1\nRELEASE = 2\n')
        expected_results = (('', ''),
                            ('1', ''),
                            ('', '2'),
                            ('1', '2'),
                            ('', '2'))
        for test_input, expected_result in zip(inputs, expected_results):
            with tempfile.NamedTemporaryFile() as f:
                f.write(test_input)
                f.flush()
                self.assertEqual(osinfo._parse_node_version(f.name),
                                 expected_result)

    @MonkeyPatch(numa, 'memory_by_cell', lambda x: {
        'total': '49141', 'free': '46783'})
    @MonkeyPatch(numa, '_get_libvirt_caps', lambda: _getTestData(
        "caps_libvirt_amd_6274.out"))
    def testNumaTopology(self):
        # 2 x AMD 6272 (with Modules)
        t = numa.topology()
        expectedNumaInfo = {
            '0': {'cpus': [0, 1, 2, 3, 4, 5, 6, 7], 'totalMemory': '49141'},
            '1': {'cpus': [8, 9, 10, 11, 12, 13, 14, 15],
                  'totalMemory': '49141'},
            '2': {'cpus': [16, 17, 18, 19, 20, 21, 22, 23],
                  'totalMemory': '49141'},
            '3': {'cpus': [24, 25, 26, 27, 28, 29, 30, 31],
                  'totalMemory': '49141'}}
        self.assertEqual(t, expectedNumaInfo)

    @MonkeyPatch(numa, '_get_libvirt_caps', lambda: _getTestData(
        'caps_libvirt_ibm_S822L_le.out'))
    @MonkeyPatch(numa, 'memory_by_cell', lambda x: {
        'total': '1', 'free': '1'})
    def testNumaNodeDistance(self):
        t = numa.distances()
        expectedDistanceInfo = {'0': [10, 20, 40, 40],
                                '1': [20, 10, 40, 40],
                                '16': [40, 40, 10, 20],
                                '17': [40, 40, 20, 10]}
        self.assertEqual(t, expectedDistanceInfo)

    @MonkeyPatch(commands, 'execCmd', lambda x, raw: (0, ['0'], []))
    def testAutoNumaBalancingInfo(self):
        t = numa.autonuma_status()
        self.assertEqual(t, 0)

    def testLiveSnapshotNoElementX86_64(self):
        '''old libvirt, backward compatibility'''
        capsData = self._readCaps("caps_libvirt_amd_6274.out")
        support = caps._getLiveSnapshotSupport(cpuarch.X86_64,
                                               capsData)
        self.assertTrue(support is None)

    def testLiveSnapshotX86_64(self):
        capsData = self._readCaps("caps_libvirt_intel_i73770.out")
        support = caps._getLiveSnapshotSupport(cpuarch.X86_64,
                                               capsData)
        self.assertEqual(support, True)

    def testLiveSnapshotDisabledX86_64(self):
        capsData = self._readCaps("caps_libvirt_intel_i73770_nosnap.out")
        support = caps._getLiveSnapshotSupport(cpuarch.X86_64,
                                               capsData)
        self.assertEqual(support, False)

    def test_findLiveSnapshotSupport(self):
        capsFile = self._readCaps("caps_libvirt_intel_i73770_nosnap.out")
        capsData = ET.fromstring(capsFile)

        guests = capsData.findall('guest')

        result = caps._findLiveSnapshotSupport(guests[0])
        self.assertIsNone(result)

        result = caps._findLiveSnapshotSupport(guests[1])
        self.assertFalse(result)

        capsFile = self._readCaps("caps_libvirt_intel_i73770.out")
        capsData = ET.fromstring(capsFile)

        guests = capsData.findall('guest')

        result = caps._findLiveSnapshotSupport(guests[0])
        self.assertIsNone(result)

        result = caps._findLiveSnapshotSupport(guests[1])
        self.assertTrue(result)

    def test_findLiveSnapshotSupport_badData(self):
        # XML which completely does not fit the schema expected
        caps_string = "<a><b></b></a>"
        caps_data = ET.fromstring(caps_string)
        result = caps._findLiveSnapshotSupport(caps_data)
        self.assertIsNone(result)

    def test_getLiveSnapshotSupport(self):
        # Using any caps file to test the correctness of parsing
        capsData = self._readCaps("caps_libvirt_intel_i73770_nosnap.out")
        UNSUPPORTED_ARCHITECTURE = 'i686'

        result = caps._getLiveSnapshotSupport(UNSUPPORTED_ARCHITECTURE,
                                              capsData)
        self.assertIsNone(result)

        result = caps._getLiveSnapshotSupport(cpuarch.X86_64,
                                              capsData)
        self.assertFalse(result)

        capsData = self._readCaps("caps_libvirt_intel_i73770.out")

        result = caps._getLiveSnapshotSupport(UNSUPPORTED_ARCHITECTURE,
                                              capsData)
        self.assertIsNone(result)

        result = caps._getLiveSnapshotSupport(cpuarch.X86_64,
                                              capsData)
        self.assertTrue(result)

    def test_getAllCpuModels(self):
        result = machinetype.cpu_models(capfile=self.CPU_MAP_FILE,
                                        arch=cpuarch.X86_64)
        expected = {
            'qemu32': None,
            'Haswell': 'Intel',
            'cpu64-rhel6': None,
            'cpu64-rhel5': None,
            'Broadwell': 'Intel',
            'pentium2': None,
            'pentiumpro': None,
            'athlon': 'AMD',
            'Nehalem': 'Intel',
            'Conroe': 'Intel',
            'kvm32': None,
            'pentium': None,
            'Opteron_G3': 'AMD',
            'coreduo': 'Intel',
            'Opteron_G1': 'AMD',
            'Opteron_G5': 'AMD',
            'Opteron_G4': 'AMD',
            'core2duo': 'Intel',
            'Penryn': 'Intel',
            'qemu64': None,
            'phenom': 'AMD',
            'Opteron_G2': 'AMD',
            '486': None,
            'Westmere': 'Intel',
            'pentium3': None,
            'n270': 'Intel',
            'SandyBridge': 'Intel',
            'kvm64': None
        }
        self.assertEqual(expected, result)

    def test_getAllCpuModels_noArch(self):
        result = machinetype.cpu_models(capfile=self.CPU_MAP_FILE,
                                        arch='non_existent_arch')
        self.assertEqual(dict(), result)

    def test_get_emulated_machines(self):
        capsData = self._readCaps("caps_libvirt_intel_i73770_nosnap.out")
        result = set(machinetype.emulated_machines('x86_64', capsData))
        expected = {'rhel6.3.0', 'rhel6.1.0', 'rhel6.2.0', 'pc', 'rhel5.4.0',
                    'rhel5.4.4', 'rhel6.4.0', 'rhel6.0.0', 'rhel6.5.0',
                    'rhel5.5.0'}
        self.assertEqual(expected, result)

    def test_get_emulated_machinesCanonical(self):
        capsData = self._readCaps("caps_libvirt_intel_E5606.out")
        result = set(machinetype.emulated_machines('x86_64', capsData))
        expected = {'pc-i440fx-rhel7.1.0',
                    'rhel6.3.0',
                    'pc-q35-rhel7.0.0',
                    'rhel6.1.0',
                    'rhel6.6.0',
                    'rhel6.2.0',
                    'pc',
                    'pc-q35-rhel7.1.0',
                    'q35',
                    'rhel6.4.0',
                    'rhel6.0.0',
                    'rhel6.5.0',
                    'pc-i440fx-rhel7.0.0'}
        self.assertEqual(expected, result)

    def test_get_emulated_machinesWithTwoQEMUInstalled(self):
        capsData = self._readCaps("caps_libvirt_multiqemu.out")
        result = set(machinetype.emulated_machines('x86_64', capsData))
        expected = {'pc-i440fx-rhel7.1.0',
                    'rhel6.3.0',
                    'pc-q35-rhel7.0.0',
                    'rhel6.1.0',
                    'rhel6.6.0',
                    'rhel6.2.0',
                    'pc',
                    'pc-q35-rhel7.1.0',
                    'q35',
                    'rhel6.4.0',
                    'rhel6.0.0',
                    'rhel6.5.0',
                    'pc-i440fx-rhel7.0.0'}
        self.assertEqual(expected, result)

    @MonkeyPatch(numa, 'memory_by_cell', lambda x: {
        'total': '1', 'free': '1'})
    def test_topology(self):
        capsData = self._readCaps("caps_libvirt_intel_i73770_nosnap.out")
        result = numa.topology(capsData)
        # only check cpus, memory does not come from file
        expected = [0, 1, 2, 3, 4, 5, 6, 7]
        self.assertEqual(expected, result['0']['cpus'])

    @MonkeyPatch(numa, 'memory_by_cell', lambda x: {
        'total': '1', 'free': '1'})
    def test_getCpuTopology(self):
        capsData = self._readCaps("caps_libvirt_intel_i73770_nosnap.out")
        t = numa.cpu_topology(capsData)
        self.assertEqual(t.threads, 8)
        self.assertEqual(t.cores, 4)
        self.assertEqual(t.sockets, 1)
        self.assertEqual(t.online_cpus,
                         ['0', '1', '2', '3', '4', '5', '6', '7'])
