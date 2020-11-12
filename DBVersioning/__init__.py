""" DBVersioning

    DBVersioning is fundamentally a high-level, agnostic collection of utilities for
    implementing version control.

    The basic workflow is:
    * Create an instance of your Database
    * Create a DBInterface for the flavor of Database you are using.
    * Create a VersionManager, passing it the DBInterface
    * Supply the VersionManager with the desired StateVersion Subclass Objects to describe the current
        layout of your Database
    
    Supplying a StateVersion of a State that is not registered with your Database will automatically instantiate it.
    Supplying a StateVersion of a State that has a greater DotVersion than a currently registered StateVersion
        with the same State will automatically update the database.
    Supplying a StateVersion of a State that is less than the currently registered StateVersion with the same State
        will result in a RollbackWarning if VersionManager.rollback_warnings is True (default), otherwise it will
        raise a RollbackError.
        To rollback a State, call VersionManager.rollback(Currently Registered StateVersion)

    See DotVersion for more information on its Syntax.
    See StateVersion for examples.
"""
## This Module
from DBVersioning.utilities import *
## Builtin Module
import functools, warnings
## Third Party Module
from DotVersion import DotVersion

class DBInterface():
    """ As DBVersioning is DB-agnostic it only requires that DBInterfaces should provide a check_version method to determine
        what version of each State is currently registered. This Mixin is therefore provided to assist in development as a reminder
        to define that method.

        Keep in mind DBInterfaces should generally also make sure any resources required to execute check_version are
        available at time of instantiation (ex.- the SQLite3Interface makes sure that the __states Table exists in
        the Database as part of the __init__ function).

        DBInterfaces and StateVersions are expected to coordinate how version numbers are stored for lookup via
        check_version. This should typically happen at the end of StateVersion.apply_update's execution.
    """
    def check_version(self, state):
        """ Objects that act as a DBInterface and implement check_version should accept both State and
            StateVersion objects as a valid argument and return the current version registered (as a
            string or DotVersion instance) for the given State.
        """
        ## _statecheck is provided for your convenience to make the state argument uniform
        state_to_check = self._statecheck(state)
        raise NotImplementedError(f"check_version not implemented on {self.__class__.__name__}")

    @classmethod
    def _statecheck(cls, state):
        """ Convenient Method for making sure the argument provided to check_version is either a State or State Version
            and, if it is a StateVersion, convert it to a State for lookup by whatever method is necessary. """
        try:
            if issubclass(state, StateVersion):
                state = state.state
        except TypeError:
            if isinstance(state, StateVersion):
                state = state.state
        try:
            issubclass(state, State)
        except TypeError:
            if not isinstance(state, State):
                raise TypeError(f"check_version accepts only State and StateVersion objects, not {state.__class__.__name__}")
        else:
            if not issubclass(state, State):
                raise TypeError(f"check_version accepts only State and StateVersion objects, not {state.__class__.__name__}")

        return state

class VersionManager():
    """ A High Level interface for managing the versions of tables included in a database """
    def __init__(self, dbinterface, versions = None, deprication_warnings = True, rollback_warnings = True):
        """ Initialize a new VersionManager.
        
            dbinterface should be an instance of a DBInterface subclass for the given flavor of your database.
            versions should be a list of StateVersions to check at initialization.
            If deprication_warnings is True (default), any depricated versions throw DepricationWarnings instead
                of DepricationErrors.
            If rollback_warnings is True (default), registering a StateVersion less than the currently registered
                one results in a RollbackWarning; otherwise, a RollbackError will be raised.
        """

        self.dbinterface = dbinterface
        self.deprication_warnings = deprication_warnings
        self.rollback_warnings = rollback_warnings
        self._states = {}
        self.register_versions(*versions)

    def detach_interface(self):
        """ Simply clears the VersionManager's reference to resources """
        self.dbinterface = None
        self._states = {}

    def register_versions(self, *versions):
        for version in versions:
            currentversion = self.dbinterface.check_version(version)
            if isinstance(currentversion, str): currentversion = DotVersion(currentversion)
            if currentversion:
                if version > currentversion:
                    try: previous_version = version.find_previous_version(currentversion)
                    except VersionNotFoundError:
                        raise VersionNotFoundError(f'Could not find an upgrade path for State "{version.state.name}" from version {currentversion} to {version.version}')
                    version.upgrade(self.dbinterface, previous_version)
                elif version < currentversion:
                    if self.rollback_warnings:
                        warnings.warn("Version being registered is lower than the currently registered Version: use StateVersion.rollback to execute rollback", RollbackWarning)
                    else:
                        raise RollbackError("Version being registered is lower than the currently registered Version: use StateVersion.rollback to execute rollback")
                ## else version == currentversion: Do nothing
            else: ## No Current Version
                version.upgrade(self.dbinterface, None)
            self._states[version.state] = version

    def rollback(self, state):
        """ Call rollback on the StateVersion currently registered with the given State. The exact result of this is up
            to the StateVersion itself, but typically the result should match the previous StateVersion. If the StateVersion
            returns another StateVersion object, that object will be the new, registered StateVersion for the State; if
            the rollback returns None, then the State will be removed from registered states altogether.
        """
        try:
            if issubclass(state, StateVersion): state = state.state
        except TypeError: pass
        try:
            if not isinstance(state, State) and not issubclass(state, State):
                raise TypeError("rollback requires a State or StateVersion")
        except TypeError: ## Type Error from issubclass; use our error instead
            raise TypeError("rollback requires a State or StateVersion")

        stateversion = self._states[state]
        result = stateversion.rollback(self.dbinterface)
        if result is None: del self._states[state]
        else:
            try:
                if isinstance(result, StateVersion) or issubclass(result,StateVersion):
                    self._states[state] = result
            except TypeError:
                raise ValueError(f"Invalid rollback result for {state}: {result}")


class State():
    """ A State which is described by its accompanying StateVersions, which are effectively changelogs.
    
        It can be useful to subclass State in order to share resources or establish constants across StateVersions.
    """
    def __init__(self, name):
        self.name = name


class Version(type):
    def __eq__(self, other):
        if isinstance(other, str):
            version = DotVersion(other)
        elif isinstance(other, DotVersion):
            version = other
        else:
            try:
                version = other.version
            except AttributeError:
                return NotImplemented
        return self.version == version
    def __ne__(self, other):
        op_result = self == other
        return op_result if op_result is NotImplemented else not op_result
    def __lt__(self, other):
        if isinstance(other, str):
            version = DotVersion(other)
        elif isinstance(other, DotVersion):
            version = other
        else:
            try:
                 version = other.version
            except AttributeError:
                return NotImplemented
        return self.version < version
    def __le__(self, other):
        op_result = self == other
        return op_result if op_result is NotImplemented else op_result or self < other
    def __gt__(self, other):
        op_result = self <= other
        return op_result if op_result is NotImplemented else not op_result
    def __ge__(self, other):
        op_result = self < other
        return op_result if op_result is NotImplemented else not op_result


class StateVersion(metaclass=Version):
    """ The Base Class for StateVersions.

        When subclassing, set the STATE value to the corresponding State instance and VERSION to the correct DotVersion
            for the new subclass. PREVIOUSVERSION should be either a StateVersion, or None (see VersionManager.rollback).
        Subclasses are recommended to supply code for apply_update and apply_rollback which will be used for version control.                
    """
    STATE = None
    VERSION = None
    PREVIOUSVERSION = None

    @classproperty
    def state(cls):
        if not cls.STATE: raise NotImplementedError("StateVersion has no State instance.")
        if not isinstance(cls.STATE, State): raise TypeError("StateVersion's State is not a State instance.")
        return cls.STATE

    @classproperty
    def version(cls):
        if not cls.VERSION: raise NotImplementedError("StateVersion has no Version.")
        version = cls.VERSION
        if isinstance(version, str): version = DotVersion(cls.VERSION)
        if not isinstance(version, DotVersion): raise TypeError("StateVersion's Version is not a String or a DotVersion instance.")
        return version

    @classproperty
    def previous_version(cls):
        if not cls.PREVIOUSVERSION: return None
        try:
            if not issubclass(cls.PREVIOUSVERSION, StateVersion): raise TypeError("StateVersion's Previous Version is not a StateVersion")
        except TypeError:
            if not isinstance(cls.PREVIOUSVERSION, StateVersion): raise TypeError("StateVersion's Previous Version is not a StateVersion")
        if cls.state != cls.PREVIOUSVERSION.state: raise ValueError("StateVersion's Previous Version does not have the same State instance")
        return cls.PREVIOUSVERSION

    @classproperty
    def is_base_verison(cls):
        return not bool(cls.PREVIOUSVERSION)

    @classmethod
    def rollback(cls, dbinterface):
        """ Rollback to the StateVersion's previous_version.

            This method returns cls.previous_version by default, which is the result expected by VersionManager.rollback().
        """
        cls.apply_rollback(dbinterface)
        return cls.previous_version

    @classmethod
    def upgrade(cls, dbinterface, from_version):
        """ Prepares the Database to upgrade from the currently implemented StateVersion. Once complete, the actual upgrade is performed by apply_upgrade().

            dbinterface is the VersionManager's dbinterface.
            from_version is the StateVersion currently implemented in the Database.

            Subclasses should overwrite the apply_upgrade function with all code required to perform the upgrade from the PREVIOUSVERSION
        """
        ## No currently installed version
        if not from_version:
            ## If this is not the base version, cannot determine what version to upgrade from
            if not cls.is_base_verison:
                cls.previous_version.upgrade(dbinterface, None)
            ## Otherwise (this is base version), continue with upgrade
            return cls.apply_upgrade(dbinterface)

        ## It is invalid to upgrade to a lower version (see rollback)
        if from_version > cls:
            raise AttributeError("Cannot upgrade to a lesser version (see StateVersion.rollback)")

        ## If the currently registered version of the Database is this StateVersion, no upgrade is necessary
        if from_version == cls: return

        if from_version < cls.previous_version:
            cls.previous_version.upgrade(dbinterface, from_version)

        ## At this point from_version is garaunteed to equal cls.previous_version, so we can upgrade
        return cls.apply_upgrade(dbinterface)

    @classmethod
    def apply_upgrade(cls, dbinterface):
        """ Performs the actual Database upgrade.

            Should be overwritten by subclasses. Unlike some other functions, does not throw a NotImplementedError
            if not overwritten.

            Subclasses should accept dbinterface, which is the dbinterface of a VersionManager to which this StateVersion is registered.
        """
        return

    @classmethod
    def apply_rollback(cls, dbinterface):
        """ Performs the actual Database rollback.

            Should be overwritten by subclasses. Unlike some other functions, does not throw a NotImplementedError
            if not overwritten.

            Subclasses should accept dbinterface, which is the dbinterface of a VersionManager to which this StateVersion is registered.
        """
        return

    @classmethod
    def find_previous_version(cls, versionnumber):
        """ Attempts to locate the given version number in the StateVersion's recursive upgrade path.
        
            If the version number does not exist, a ValueError is raised.
        """
        if isinstance(versionnumber, str): versionnumber = DotVersion(versionnumber)
        if not isinstance(versionnumber, DotVersion): raise TypeError(f"Version number should be a string or DotVersion")
        if not cls.previous_version: raise VersionNotFoundError(f"Could not locate version number: {versionnumber}")
        if cls.previous_version == versionnumber: return cls.previous_version
        return cls.previous_version.find_previous_version(versionnumber)