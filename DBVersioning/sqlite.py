""" DBVersioning.sqlite3

SQLite3 interfaces for use with the VersionManager.


The SQLite3Interface subclasses sqlite3.Connection, and therefore is a drop-in replacement
for sqlite3.connect().

On the backend, SQLite3Interface uses a Table called "__states" to manage StateVersions.
This table uses the State name as a Unique Key and saves the installed StateVersion's
Version as a string.

To update the "__states" Table, SQLite3Interface.set_version should be used when moving
between StateVersions (update or rollback) or .remove_version when the State is completely
rolled back.

To make this easier, this module supplies its own version of the StateVersion super class
which automatically calls set_version or remove_version as necessary after executing upgrade
and rollback.
"""
## Builtin Module
import sqlite3
## This Module
from DBVersioning import DBInterface, StateVersion as SV

class SQLite3Interface(sqlite3.Connection, DBInterface):
    """ SQLite3Interface is a Connection subclass DBInterface: this means that it has all the
        functionality of a Connection object (the return of sqlite3.connect()) as well as implementing
        the required methods to qualify as a DBInterface.
    """
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.row_factory = sqlite3.Row
        self.check_versiontable()
        
    def get_versiontable(self):
        return self.execute("""SELECT * FROM __states;""").fetchall()

    def check_versiontable(self):
        try: self.get_versiontable()
        except sqlite3.OperationalError:
            self.execute("""CREATE TABLE __states (state TEXT UNIQUE, version TEXT);""")
            try:
                self.get_versiontable()
            except:
                raise RuntimeError(f"{self.__class__.__name__} could not create __states table")

    def check_version(self, state):
        state = self._statecheck(state)
        results = self.get_versiontable()
        for result in results:
            if result['state'] == state.name:
                return result['version']

    def set_version(self, stateversion):
        """ Registers or Updates a State's Version in the __states table """
        state = stateversion.state.name
        version = str(stateversion.version)
        self.execute("""INSERT INTO __states (state, version) VALUES (:state, :version) ON CONFLICT (state) DO UPDATE SET version=excluded.version;""", dict(state = state, version=version))

    def remove_version(self, state):
        """ Removes a State from the __states table: ensure the State is completely rolled back before calling this method. """
        state = state.name
        self.execute("""DELETE FROM __states WHERE state = :state;""", dict(state = state))

class StateVersion(SV):
    @classmethod
    def upgrade(cls, dbinterface, from_version):
        super().upgrade(dbinterface, from_version)
        dbinterface.set_version(cls)
    
    @classmethod
    def rollback(cls, dbinterface):
        result = super().rollback(dbinterface)
        if result is not None: dbinterface.set_version(result)
        else: dbinterface.remove_version(cls.state)
        return result