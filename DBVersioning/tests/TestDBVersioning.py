""" DBVersioning.tests.DBVersioningTests.py

    Tests for Classes and Functions in DBVersioning.__init__

"""
## Test Framework
import unittest
## Test Target
import DBVersioning

## This Module
from DBVersioning import utilities

class VersionCase(unittest.TestCase):
    """ Test Case for the Version Metaclass """
    class PureVersion(metaclass = DBVersioning.Version):
        VERSION = None
        @utilities.classproperty
        def version(cls):
            if cls.VERSION is None: raise NotImplementedError("Test does not declare VERSION")
            return cls.VERSION

    def test_versioncomparison(self):
        """ Basic test case for the Version metaclass: ensuring that Version Classes are comparable. """
        class Version1(VersionCase.PureVersion):
            VERSION = "1.0"

        class Version2(VersionCase.PureVersion):
            VERSION = "2.0"

        class Version1_1(VersionCase.PureVersion):
            VERSION = "1.1"

        class Version1Again(VersionCase.PureVersion):
            VERSION = "1.0"

        self.assertGreater(Version2, Version1)
        self.assertGreaterEqual(Version2, Version1)
        self.assertGreaterEqual(Version2, Version2)
        self.assertGreater(Version1_1, Version1)
        self.assertLess(Version1, Version1_1)
        self.assertLessEqual(Version1, Version1_1)
        self.assertLessEqual(Version1, Version1)
        self.assertEqual(Version1, Version1)
        self.assertEqual(Version1, Version1Again)
        self.assertNotEqual(Version1, Version1_1)

        ## Sortability is not really a prerequisite at a minute, but should work anyway
        testlist = [Version2, Version1Again, Version1_1, Version1]
        self.assertEqual(sorted(testlist), [Version1Again, Version1, Version1_1, Version2])

class StateVersionCase(unittest.TestCase):
    """ Test Case for the StateVersion base class """
    def test_interoperability(self):
        """ Makes sure that StateVersion is interoperable with Strings and DotVersion """
        class MyStateVersion(DBVersioning.StateVersion):
            VERSION = "1.0"

        DotVersion = DBVersioning.DotVersion

        self.assertGreater(MyStateVersion, "0.0")
        self.assertLess(MyStateVersion, "2.0")
        self.assertGreater(MyStateVersion, DotVersion("0.1"))
        self.assertLess(MyStateVersion, DotVersion("3.5"))

if __name__ == "__main__":
    unittest.main()