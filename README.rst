Borg-Space — Report and track the size of your Borg repositories
================================================================

.. image:: https://pepy.tech/badge/borg-space/month
    :target: https://pepy.tech/project/borg-space

.. image:: https://img.shields.io/pypi/v/borg-space.svg
    :target: https://pypi.python.org/pypi/borg-space

.. image:: https://img.shields.io/pypi/pyversions/borg-space.svg
    :target: https://pypi.python.org/pypi/borg-space/

:Author: Ken Kundert
:Version: 2.0
:Released: 2023-05-15

*Borg-Space* is an accessory for Emborg_.  It reports on the space consumed by 
your *BorgBackup* repositories.  You can get this information using the ``emborg 
info`` command, but there are several reasons to prefer *Borg-Space*.

#. *Borg-Space* reports on many repositories at once.
#. The *Emborg* *info* command gives a great deal of information,
   whereas *Borg-Space* only reports the space consumed by the repository,
   so is much more compact.
#. The report is user customizable.
#. *Borg-Space* can record the size of your repositories each time it is run
   so you can track the space requirements over time.
#. Finally, *Borg-Space* can graph the recorded values.

To show the size of one or more repositories, simply run::

    # borg-space home
    home: 12.81 GB

You can specify any number of repositories, and they can be composite
configs::

    > borg-space home cache
    borgbase: 2.44 GB
    cache: 801 MB
    rsync: 2.81 GB

You can specify repositories that are owned by others or that are on remote 
machines.  In this case you will need permission to read the *Emborg* data 
directory for the repository. Specifically, 
❬host❭:~❬user❭/.local/share/emborg/❬config❭.latest.nt must be accessible.
To specify these repositories, a special naming scheme is used::

    ❬config❭@❬host❭~❬user❭

Thus the *Emborg* configuration named *primary* owned by *root* on the host with 
the SSH name *neptune* is accessed with::

    # borg-space primary@neptune~root
    primary@neptune~root: 57.74 GB


Usage
-----

*Borg-Space* supports the following command line arguments::

    Usage:
        borg-space [--quiet] [--style <style>] [--record] [<repo>...]
        borg-space [--graph] [--svg <file>] [--log-y] [<repo>...]

    Options:
        -r, --record                 save the result
        -q, --quiet                  do not output the size message
        -s <style>, --style <style>  the report style
                                     choose from compact, normal, tree, nt, json
        -g, --graph                  graph the previously recorded sizes over time
        -l, --log-y                  use a logarithmic Y-axis when graphing
        -S <file>, --svg <file>      produce plot as SVG file rather than display it



Settings
--------

You can create a NestedText_ settings file to specify default behaviors and 
define composite repositories.  For example::

    default repository: home
    report style: tree
    compact format: {repo}: {size:{fmt}}.  Last back up: {last_create:ddd, MMM DD}.  Last squeeze: {last_squeeze:ddd, MMM DD}.
    normal format: {host:<8} {user:<5} {config:<9} {size:<8.2b} {last_create:ddd, MMM DD}
    normal header: HOST     USER  CONFIG    SIZE     LAST BACK UP
    report fields: size last_create last_squeeze
    tree report fields: size
    date format: D MMMM YYYY
    size format: .b
    nestedtext size format: .3b

    repositories:
        home:
            children: rsync borgbase
        servers:
            children:
                - root@dev~root
                - root@mail~root
                - root@files~root
                - root@bastion~root
                - root@media~root
                - root@web~root
        all:
            children: home servers

default repository:
    The name of the repository to be used if one is not given on the command 
    line.

report style:
    The report style to be used if none is specified on the command line.  
    Choose from *compact*, *normal*, *tree*, *nestedtext* or *nt*, or *json*.

compact format:
    The format to be used for the line when the requested report style is 
    *compact*.
    The *repo*, *size*, *fmt*, *last_create*, *last_prune*, *last_compact* and 
    *last_squeeze*  fields will be replaced by the corresponding values.
    *last_squeeze* is simply the later of *last_prune* and *last_compact*.  
    *size* is a QuantiPhy_ *Quantity* and the *last_* fields are all Arrow_ 
    objects.  The remaining field values are strings.

    The default is::

        {repo}: {size:{fmt}}

normal format:
    The format to be used for the line when the requested report style is 
    *normal*.  The *host*, *user*, *config*, *size*, *fmt*, *last_create*, 
    *last_prune*, *last_compact* and *last_squeeze*  fields will be replaced by 
    the corresponding values.  *last_squeeze* is simply the later of 
    *last_prune* and *last_compact*.  *size* is a QuantiPhy_ *Quantity* and the 
    *last_* fields are all Arrow_ objects.  The remaining field values are 
    strings.

    The default is::

        {host:8} {user:8} {config:8} {size:<8.2b}  {last_create:ddd, MMM DD}

normal header:
    The header to be printed just before the normal report.  It is used to give 
    column headers.  Leave empty to suppress the header.

    The default is::

        HOST     USER     CONFIG   SIZE      LAST BACK UP

report fields:
    The fields to include in *tree*, *nestedtext* and *json* style reports by 
    default.  Default is *size*, *last_create*, and *last_squeeze*.

tree report fields:
    The fields to include in *tree* style reports.
    default.  If not given it defaults to the value of  *report fields*.

nestedtext report fields:
    The fields to include in *nestedtext* style reports.
    default.  If not given it defaults to the value of *report fields*.

json report fields:
    The fields to include in *json* style reports.
    default.  If not given it defaults to the value of  *report fields*.

size format:
    The format to be used when giving the size of the repository.  This is 
    a QuantiPhy_ format string.  In the example, ``.2b`` means that a binary 
    format with two extra digits is used (one digit is required. so ``.2b`` 
    prints with three digits of precision.  If not give, it defaults to ``.2b``.

nestedtext size format:
    The format to be used for the size of the repository when the requested 
    report style is jnestedtext*.  This is a QuantiPhy_ format string.  If not 
    given, it defaults to *size format*.

date format:
    The Arrow_ format to be used for the date when the requested report style is 
    *tree* or *nestedtext*.  If not given, it defaults to ``D MMMM YYYY``.

repositories:
    Predefines available repositories.  This generally used to define composite 
    repositories.  In this way, one name can be used for many repositories.


Graphing
--------

To graph the size of a repository over time you must first routinely record its 
size.  You can record the sizes with::

    > borg-space -r home

The sizes are added to the file ``~/.local/share/borg-space/❬repo❭.nt``.

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
        'borg-space -r {config_name}'
    ]

Once you have recorded some values, you can graph them using::

    > borg-space -g home

This displays the graph on the screen. Alternately, you can save the graph to 
a file in SVG format using::

    > borg-space -S home.svg home

I routinely monitor the repositories for over a dozen hosts, and to make it 
convenient I create a composite *Emborg* configuration containing all the hosts, 
and then use the ``--log-y`` option so that I can easily see all the results 
scaled nicely on the same graph::

    > borg-space -l all


Installation
------------

*Borg-Space* requires *Emborg* version 1.36 or newer.

Install with::

    > pip3 install borg-space


.. _emborg: https://emborg.readthedocs.io
.. _nestedtext: https://nestedtext.org
.. _arrow: https://arrow.readthedocs.io/en/latest/guide.html#supported-tokens
.. _quantiphy: https://quantiphy.readthedocs.io/en/stable/api.html#quantiphy.Quantity.format
