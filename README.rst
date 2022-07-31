Borg-Space — Report and track the size of your Borg repositories
================================================================

.. image:: https://pepy.tech/badge/borg-space/month
    :target: https://pepy.tech/project/borg-space

.. image:: https://img.shields.io/pypi/v/borg-space.svg
    :target: https://pypi.python.org/pypi/borg-space

.. image:: https://img.shields.io/pypi/pyversions/borg-space.svg
    :target: https://pypi.python.org/pypi/borg-space/

:Author: Ken Kundert
:Version: 0.3.0
:Released: 2022-03-21

*Borg-Space* is an accessory for `Emborg <https://emborg.readthedocs.io>`_.  It
reports on the space consumed by your *BorgBackup* repositories.  You can get
this information using the ``emborg info`` command, but there are several
reasons to prefer *Borg-Space*.  First, the *info* command gives a great deal of
information, whereas *Borg-Space* only reports the space consumed by the
repository, so is much more compact.  Second, the output message is user
customizable. Third, *Borg-Space* can record the size of your repositories each
time it is run so you can track the space requirements over time.  Finally,
*Borg-Space* can graph the recorded values.

To show the size of one or more *Emborg* configurations, simply run::

    # borg-space root
    root: 2.81 GB

If you do not specify a config, you get *Emborg*'s default config.

You can specify any number of configurations, and they can be composite
configs::

    > borg-space home cache
    rsync: 2.81 GB
    borgbase: 2.44 GB
    cache: 801 MB

You can change the message by giving a template::

    > borg-space -m 'Repository for {config} is now {size}." home
    Repository for rsync is now 2.81 GB.
    Repository for borgbase is now 2.44 GB.

The *config* key takes Python string format codes and the *size* key takes
`QuantiPhy
<https://quantiphy.readthedocs.io/en/stable/user.html#string-formatting>`_
format codes::

    > borg-space -m '{config>12}: {size:b}." home
           rsync: 2.62 GiB
        borgbase: 2.26 GiB

You can record the sizes with::

    > borg-space -r home

The sizes are added to the file ``~/.local/share/emborg/{config}-size.nt``.

Typically you do not manually run *Borg-Space* to record the sizes of your
repositories.  Instead, you can record sizes automatically in two different
ways.  In the first, you simply use crontab to automatically record the sizes at
fixed times::

    00 12 * * *  borg-space -q -r home

In this case the command runs at noon every day and uses the ``-q`` option to
suppress the output to stdout.  This approach can be problematic if *Emborg*
needs access to SSH or GPG keys to run.

The other approach is to add *Borg-Space* to the *run_after_backup* setting in
your *Emborg* configs.  That way it is run every time you run backup::

    run_after_backup = [
        'borg-space -r -m "Repository is now {{size}}." {config_name}'
    ]

*Emborg* also uses braces to interpolate values, so they are doubled-up in the
*Borg-Space* command to escape them (except for removing the second brace,
*Emborg* ignores double braces).

Once you have recorded some values, you can graph them using::

    > borg-space -g home

This displays the graph on the screen. Alternately, you can save the graph to 
a file in SVG format using::

    > borg-space -s home.svg home

I routinely monitor the repositories for over a dozen hosts, and to make it 
convenient I create a composite *Emborg* configuration containing all the hosts, 
and then use the ``--log-y`` option so that I can easily see all the results 
scaled nicely on the same graph::

    > borg-space -l all


Installation
------------

Install with::

    > pip3 install --user borg-space


Releases
--------

Latest development release
..........................
| Version: 0.3.0
| Released: 2022-03-21


0.3.0 (2022-03-21)
..................
- Upgrade required to support *Emborg* version 1.31.


0.2.0 (2021-10-01)
..................
- Fixed incompatibility with *Emborg* version 1.26.


0.1.0 (2021-09-30)
..................
- Added ability to save graph as SVG file.


0.0.0 (2021-09-25)
..................
- Initial release
