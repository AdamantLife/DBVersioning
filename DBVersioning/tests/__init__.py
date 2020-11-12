""" DBVersioning.tests.__init__.py

    Contains the TestRunner for the full DBVersioning.tests module
"""
## Test Framework
import unittest

## Builtin
import pathlib

if __name__ == "__main__":
    loader = unittest.TestLoader()
    tests = loader.discover(".")
    def listtests(suite, indent = ""):
        for child in suite:
            if isinstance(child, unittest.TestSuite):
                listtests(child, indent + "  ")
            else:
                print(indent+str(child))
    print("Tests:")
    listtests(tests, "  ")
    runner = unittest.TextTestRunner()
    runner.run(tests)