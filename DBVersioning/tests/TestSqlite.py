""" DBVersioning.tests.TestSqlite.py

    Tests for DBVersioning's sqlite module
"""
## Test Framework
import unittest
## Test Target
from DBVersioning import sqlite

## This Module
from DBVersioning import State, VersionManager
## builtin
import sqlite3

state = State("Basic")

class BasicV1(sqlite.StateVersion):
    STATE = state
    VERSION = "1.0"
    @classmethod
    def apply_upgrade(cls,dbinterface):
        dbinterface.execute("""CREATE TABLE a (b);""")
    @classmethod
    def apply_rollback(cls, dbinterface):
        dbinterface.execute("""DROP TABLE a;""")

class BasicV2(sqlite.StateVersion):
    STATE = state
    VERSION = "2.0"
    PREVIOUSVERSION = BasicV1
    @classmethod
    def apply_upgrade(cls, dbinterface):
        dbinterface.execute("""CREATE TABLE c (d);""")
    @classmethod
    def apply_rollback(cls, dbinterface):
        dbinterface.execute("""DROP TABLE c;""")

class StateVersionCase(unittest.TestCase):
    """ Test Case for sqlite's StateVersion subclass """

    def test_basic(self):
        dbinter = sqlite.SQLite3Interface(":memory:")
        myvm = VersionManager(dbinter, versions = [BasicV1,])

        ## StateVersion subclass still loads automatically
        self.assertEqual(dbinter.check_version(state), "1.0")
        dbinter.execute("""INSERT INTO a VALUES ("b");""")

        ## StateVersion subclass rollsback to 0 correctly
        myvm.rollback(state)
        self.assertIsNone(dbinter.check_version(state))
        self.assertRaises(sqlite3.OperationalError, lambda: dbinter.execute("""SELECT * FROM a;""").fetchall())

        ## StateVersion subclass executes upgrade paths correctly
        myvm.register_versions(BasicV2)
        self.assertEqual(dbinter.check_version(state), "2.0")
        dbinter.execute("""INSERT INTO a VALUES ("b");""")
        dbinter.execute("""INSERT INTO c VALUES ("d");""")

        ## StateVersions subclass rolls back incremenally correctly
        myvm.rollback(state)
        self.assertEqual(dbinter.check_version(state), "1.0")
        self.assertEqual([tuple(r) for r in dbinter.execute("""SELECT * FROM a;""")], [("b",)])
        self.assertRaises(sqlite3.OperationalError, lambda: dbinter.execute("""SELECT * FROM c;""").fetchall())

class SubclassCase(unittest.TestCase):
    def test_subclass_executereturn(self):
        """ Make sure that SQLite3Interface always uses sqlite3.Connection.execute so that Subclasses can overwrite execute if desired.
        
            Additionally, this would normally lead to an OperationalError that is passed on the first check_versiontable
            try/except when the __states table is initially created, but raised with a custom message on the followup
            try/except. This can lead to confusion since the initial error may be missed in the error statck (though the
            second time check_versiontable is executed on a database the correct error is the only error given).
        """
        class SubClass(sqlite.SQLite3Interface):
            """ This is an example subclass which removes the need for calling fetchall().
                
                In the above described situation, when this is first called it raises "Could not create __states table"
                even though the table is properly created: It fails the second try/excepts with "AttributeError: 'list'
                object has no attribute 'fetchall'"
            """
            def execute(self, *args, **kw):
                return super().execute(*args, **kw).fetchall()
                
        dbinter = SubClass(":memory:")
        myvm = VersionManager(dbinter, versions = [BasicV1,])
        ## So long as the code hasn't caused an error by this point, the bug is fixed.
        ## We'll check for propriety's sake, though
        self.assertEqual(dbinter.check_version(BasicV1), BasicV1.version)
        
if __name__ == "__main__":
    unittest.main()