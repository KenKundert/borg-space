from setuptools import setup

with open("README.rst", encoding="utf-8") as file:
    readme = file.read()

setup(
    name = "borg-space",
    version = "0.2.0",
    author = "Ken Kundert",
    author_email = "emborg@nurdletech.com",
    description = "Accessory for Emborg used to report and track the size of your Borg repositories",
    long_description = readme,
    long_description_content_type = 'text/x-rst',
    url = "https://emborg.readthedocs.io",
    download_url = "https://github.com/kenkundert/borg-space/tarball/master",
    license = "GPLv3+",
    scripts = 'borg-space'.split(),
    install_requires = """
        appdirs
        arrow>=0.15
        docopt
        emborg>=1.27
        inform>=1.26
        matplotlib
        nestedtext
        quantiphy
    """.split(),
    python_requires = ">=3.6",
    zip_safe = True,
    keywords = "emborg borg backups".split(),
    #"Development Status :: 5 - Production/Stable",
    classifiers = [
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Utilities",
    ],
)
