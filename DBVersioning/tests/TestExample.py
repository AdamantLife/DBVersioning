""" DBVersioning.tests.TestExamply.py

    This module serves as both a TestCase and an Example Program to introduce the basics of the DBVersioning Module

"""

## Test Framework
import unittest
## Test Target
from DBVersioning import VersionManager, State, StateVersion

## This Module
from DBVersioning.sqlite import SQLite3Interface
## Builtin
import sqlite3

## Note that this Example will use the SQLite3 flavor of Database,
## but the general concepts shown here should be adaptable to whatever
## kind of database you are using

## CoreState is a simple Database State with no special functionality.
## A Database State is essentially a Scope within that Database of
## closely related tables/features
CoreState = State("CoreDatabase")

## Creating a subclass for CoreStateVersions for clarity and to
## avoid the error of not declaring the STATE value in future subclasses
class CoreStateVersion(StateVersion):
    STATE = CoreState

## Version 1 of the "CoreDatabase" State simply creates a Table called "users"
## and removes it on rollback
## Note that DBVersioning.sqlite provides its own StateVersion subclass which
## automatically handles state version updates after apply_upgrade and apply_rollback;
## this example does not utilize this subclass to demonstrate that the dbinterface
## should always be updated in some manner to match the change in StateVersion
class CoreStateV1(CoreStateVersion):
    VERSION = "1.0"
    ## apply_upgrade is called by StateVersion.upgrade and is used to introduce new
    ## functionality for the given State
    ## It exists as its own method to maintain code separation for subclassing
    ## Most subclasses should only overwrite this method and leave StateVersion.upgrade unchanged
    @classmethod
    def apply_upgrade(cls, dbinterface):
        dbinterface.execute("""CREATE TABLE users (name TEXT);""")
        dbinterface.set_version(cls)

    ## apply_rollback follows the same rules as apply_upgrade, but is used to undo the
    ## changes made during apply_upgrade.
    @classmethod
    def apply_rollback(cls, dbinterface):
        dbinterface.execute("""DROP TABLE users;""")
        ## As this is the first StateVersion for the "CoreDatabase" State and we are
        ## using the SQLite3 flavor of DBInterface, we should remove "CoreDatabase"
        ## as a registered State for the database using remove_state
        dbinterface.remove_state(cls.state)

## Version 2 will create a Table called Issues when upgraded, and will
## remove the Table on rollback
## StateVersions after the first all work relatively similarly
class CoreStateV2(CoreStateVersion):
    VERSION = "2.0"
    ## Since this is not the First StateVersion for the "CoreDatabase" State,
    ## we should include a link to the PREVIOUSVERSION in order to establish
    ## an upgrade/rollback path
    PREVIOUSVERSION = CoreStateV1
    @classmethod
    def apply_upgrade(cls, dbinterface):
        dbinterface.execute("""CREATE TABLE issues(user REFERENCES users, description TEXT);""")
        dbinterface.set_version(cls)
    @classmethod
    def apply_rollback(cls, dbinterface):
        dbinterface.execute("""DROP TABLE issues;""")
        ## Unlike CoreStateV1, if we rollback the changes made in CoreStateV2 the
        ## Database will still have the aspects defined by previous StateVersions
        ## Therefore we use set_version(cls.previous_version) instead of remove_version
        dbinterface.set_version(cls.previous_version)

## Version 2.1 adds the "role" column to users and adds an "assigned" column to Issues
## As noted above, there is no structural difference between StateVersions after the
## first: the differences you may notice in this one are merely due to this example
## using SQLite3 syntax.
class CoreStateV2_1(CoreStateVersion):
    VERSION = "2.1"
    PREVIOUSVERSION = CoreStateV2
    @classmethod
    def apply_upgrade(cls, dbinterface):
        dbinterface.executescript("""ALTER TABLE users ADD COLUMN role; ALTER TABLE issues ADD COLUMN assigned REFERENCES users;""")
        dbinterface.set_version(cls)
    @classmethod
    def apply_rollback(cls, dbinterface):
        dbinterface.executescript("""
        -- Recreate users with no role column (no Drop Column syntax available)
        CREATE TEMP TABLE users2 (rowid INTEGER, name TEXT);
        INSERT INTO users2 SELECT rowid, name FROM users;
        DROP TABLE users;
        CREATE TABLE users (name TEXT);
        INSERT INTO users (rowid, name) SELECT rowid, name FROM users2;
        DROP TABLE user2;

        -- Recreate issues with no role column (no Drop Column syntax available)
        CREATE TEMP TABLE issues2 (rowid INTEGER, user INTEGER, description TEXT);
        INSERT INTO issues2 SELECT rowid, user, description FROM users;
        DROP TABLE issues;
        CREATE TABLE issues (user REFERENCES users, description TEXT);
        INSERT INTO issues(rowid, user, description) SELECT rowid, user, description FROM issues2
        DROP TABLE issues2;
        """)
        dbinterface.set_version(cls.previous_version)

class StateVersionExampleCase(unittest.TestCase):
    def test_example(self):
        ## This method is simply used to aid in testing and is
        ## irrelevant to the example
        def to_tuple(rows):
            return [tuple(row) for row in rows]

        #Normally you would use something like "from SomeModule import MyDBInterface"
        ## In this example we'll be using SQLite3Interface and are simply renaming it
        ## to mimic the idea that we may be using a custom DBInterface
        MyDBInterface = SQLite3Interface

        ## For this example we'll be initializing Database Interface in memory
        dbinter = MyDBInterface(":memory:")

        ## Here we initialize VersionManager with CoreStateV1 already registered
        ## If CoreStateV1 wasn't previously registered, it's upgrade() method will be called
        ## and the *users* Table will be created. Regardless of whether it was already
        ## registered with the Database/DBInterface, the VersionManager will add the
        ## State and StateVersion to its own index of registered StateVersions 
        myvm = VersionManager(dbinter, versions = [CoreStateV1,])

        ## The Database/DBInterface now has the "CoreDatabase" State registered with StateVersion "1.0"
        self.assertEqual(dbinter.check_version(CoreState), CoreStateV1.version)
        self.assertEqual(CoreStateV1.version, "1.0")

        ## The Database now has the *users* Table which we can use
        dbinter.execute("""INSERT INTO users VALUES ("Alice"), ("Bob");""")
        ## This should return 2 rows: ("Alice",) and ("Bob,")
        result = dbinter.execute("""SELECT * FROM users;""").fetchall()
        self.assertEqual(to_tuple(result), [("Alice",), ("Bob",)])

        ## Now we'll upgrade the "CoreDatabase" State to Version "2.0" using
        ## VersionManager.register_versions()
        myvm.register_versions(CoreStateV2)
        ## The "CoreDatabase" State is now registered with StateVersion "2.0"
        self.assertEqual(dbinter.check_version(CoreState), CoreStateV2.version)
        self.assertEqual(CoreStateV2.version, "2.0")

        ## The Database now has the *issues* Table to which we'll insert some values
        dbinter.execute("""INSERT INTO issues VALUES (1,"Database doesn't work");""")
        ## This should return the row we just added (substituting the foreign key for user name): ("Alice", "Database doesn't work")
        result = dbinter.execute("""SELECT users.name, issues.description FROM issues LEFT JOIN users on issues.user = users.rowid;""").fetchall()
        self.assertEqual(to_tuple(result), [("Alice", "Database doesn't work")])

        ## We'll now demonstrate how to rollback CoreDatabase with VersionManager.rollback
        myvm.rollback(CoreState)
        ## We can see that "CoreDatabase" State is now registered once again with StateVersion "1.0"
        self.assertEqual(dbinter.check_version(CoreState), CoreStateV1.version)
        self.assertEqual(CoreStateV1.version, "1.0")

        ## Since the rollback removed the *issues* table, querying on it should raise an Exception
        query_issues = lambda: dbinter.execute("""SELECT * FROM issues;""").fetchall()
        self.assertRaises(sqlite3.OperationalError, query_issues)

        ## We'll now upgrade directly from CoreDatabase Version 1.0 to 2.1
        ## This will automatically apply all upgrades in between (in this case,
        ## CoreStateVersion2)
        ## Note that this only works because CoreStateV2_1 defines PREVIOUSVERSION as CoreStateV2
        ## and CoreStateV2 lists CoreStateV1 as its PREVIOUSVERSION
        myvm.register_versions(CoreStateV2_1)
        ## "CoreDatabase" State is now registered with StateVersion "2.1"
        self.assertEqual(dbinter.check_version(CoreState), CoreStateV2_1)
        self.assertEqual(CoreStateV2_1, "2.1")

        ## The Database once again has *issues* Table (from CoreStateV2), but *issues* now also has a
        ## column named "assigned"
        ## *users* Table also now has a column named "role" which was added in CoreStateV2_1
        ## We'll add some data to the Database to check it
        dbinter.execute("""UPDATE users SET role="admin" WHERE name="Alice";""")
        dbinter.execute("""INSERT INTO issues (user, description, assigned) VALUES (2, "Database doesn't work", 1);""")
        ## We'll now query the *issues* table for all rows, and for each row we'll include the user's name,
        ## the description of the issue, the name of the user assigned to the issue, and the role of that user
        result = dbinter.execute("""SELECT u1.name, issues.description, u2.name, u2.role
        FROM issues
        LEFT JOIN users u1 ON issues.user = u1.rowid
        LEFT JOIN users u2 ON issues.assigned = u2.rowid;""").fetchall()
        ## The only resulting row we should have in the Database right now should be: ("Bob", "Database doesn't work", "Alice", "admin")
        self.assertEqual(to_tuple(result), [("Bob", "Database doesn't work", "Alice", "admin")])

        ## Once we are done managing the Database, we no longer need the VersionManager or DBInterface
        ## instances, though you may decide to use the DBInterface to perform other tasks.
        dbinter.close()
        ## detach_interface simply sets VersionManager.dbinterface to None and creates a new
        ## registry for states. It is not always necessary to call (outside of helping to
        ## prevent memory leaks)
        myvm.detach_interface()
        del dbinter
        del myvm

        ## This concludes the basic usage of DBVersioning:
        ##  * Setup
        ##  * Registering a new State with a StateVersion
        ##  * Upgrading a registered State/StateVersion (multiple upgrades can be done in one call)
        ##  * and Rolling back a StateVersion to a previous version


if __name__ == "__main__":
    unittest.main()