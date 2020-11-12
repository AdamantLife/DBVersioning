import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="DBVersioning",
    version="1.0.0",
    author="AdamantLife",
    author_email="",
    description="An Agnostic, Object-Oriented Library to implement Database Versioning",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AdamantLife/DBVersioning",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    install_requires=[
        "DotVersion @ git+https://github.com/AdamantLife/DotVersion"
        ]
)
