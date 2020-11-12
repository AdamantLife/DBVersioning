## Test Framework
import unittest
## Test Target
from DBVersioning import utilities

class ClassPropertyCase(unittest.TestCase):
    def test_classproperty(self):
        classproperty = utilities.classproperty

        class A():
            A = 1
            @classproperty
            def a(cls):
                return cls.A

        self.assertEqual(A.a, 1)

        class B(A):
            A = 2

        self.assertEqual(B.A, 2)
            

if __name__ == "__main__":
    unittest.main()