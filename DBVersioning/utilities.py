class VersionError(Exception):
    """ Base class for Version Errors """

class VersionNotFoundError(VersionError):
    """ Used when a Version cannot be found; currently just in StateVersion.find_previous_version. """

class VersionDepricationError(VersionError):
    """ Raised when a version is required by a StateVersion but a newere StateVersion depricates that version. """

class RollbackError(VersionError):
    """ Raised when the Database requires a rollback on a StateVersion. Called when VersionManager.rollbackwarning is False. """

class VersionWarning(Warning):
    """ Base class for Version Warnings """

class RollbackWarning(VersionWarning):
    """ Warning used by VersionManager to signal that the currently registered
        version is newer than the version supplied to VersionManager.register_version. """

class classproperty():
    """ As StateVersions are represented as classes, used to make properties of those classes class-accessible
    
        TODO: In python 3.9 classmethod can wrap the property method; if a future Python
        release makes it more beneficial to change the minimum version requirement then
        update code to use classmethod.
    """
    def __init__(self, fget):
        self.fget = classmethod(fget)
    def __get__(self, instance, owner = None):
        return self.fget.__get__(instance, owner)()
