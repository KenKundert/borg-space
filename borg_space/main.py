#!/usr/bin/env python3
# description {{{1
"""
Borg Space

Reports on the current size of one or more Borg repositories managed by Emborg.

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

Results are saved to ~/.local/share/borg-space/<config>.nt.
"""

# imports {{{1
from .config import settings, get_repos, split_repo_name
from .trees import tree
import arrow
from appdirs import user_data_dir
from docopt import docopt
from inform import Error, display, error, os_error
from pathlib import Path
from quantiphy import Quantity
import json
import nestedtext as nt
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.dates import AutoDateFormatter, AutoDateLocator
from matplotlib.ticker import FuncFormatter
import os
import socket
import pwd

# globals {{{1
data_dir = Path(user_data_dir('borg-space'))
now = str(arrow.now())
Quantity.set_prefs(prec='full')
__version__ = "1.0"
__released__ = "2023-04-08"
date_format = settings.get('date_format', 'D MMMM YYYY')
size_format = settings.get('size_format', '.2b')
nestedtext_size_format = settings.get('nestedtext_size_format', size_format)
size_fields = ['size',]  # must be a single value
date_fields = ['last_create', 'last_prune', 'last_compact', 'last_squeeze']
report_fields = settings.get('report_fields', size_fields)

# gethostname {{{1
# returns short version of the hostname (the hostname without any domain name)
def gethostname():
    return socket.gethostname().split('.')[0]

# getusername {{{1
def getusername():
    return pwd.getpwuid(os.getuid()).pw_name

# collect_repos() {{{1
def collect_repos(requests, record_size):
    repos = {}
    for request in requests:
        repos = get_repos(request)
        repos.update(repos)

    # record the size if requested {{{3
    if record_size:
        for name, repo in repos.items():

            # read previously recorded sizes
            data_path = Path(data_dir / f'{name}.nt')
            try:
                data = nt.load(data_path, top=dict)
            except FileNotFoundError:
                data = {}

            # append new size
            data[now] = repo['size'].fixed()

            # write out sizes
            nt.dump(data, data_path)

    return repos

# generate_graph() {{{1
def generate_graph(repos, svg_file, log_scale):
    if svg_file:
        matplotlib.use('SVG')

    # determine size history of each config's repository {{{2
    traces = []
    for name in repos:
        data_path = data_dir / f'{name}.nt'
        data = nt.load(data_path, top=dict)
        sizes = []
        dates = []
        for date, size in data.items():
            dates.append(arrow.get(date))
            sizes.append(Quantity(size, 'B').real)
        traces.append((name, Quantity(size, 'B'), dates, sizes))

    # plot the results {{{2
    # create and configure the canvas {{{3
    fig = plt.figure()
    ax = fig.add_subplot(111)
    if log_scale:
        ax.set_yscale('log')

    # configure the axis labeling {{{3
    locator = AutoDateLocator()
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(AutoDateFormatter(locator))

    # add traces in order of last size, largest to smallest {{{3
    largest = 0
    smallest = 1e100
    for entry in sorted(traces, key=lambda d: d[1], reverse=True):
        name, last_size, dates, sizes = entry
        largest = max(largest, *sizes)
        smallest = min(smallest, *sizes)
        trace, = ax.plot_date(dates, sizes, "-")
        trace.set_label(f'{name} ({last_size})')

    # use SI scale factors on Y-axis
    def bytes(y, pos=None):
        return Quantity(y, 'B').render()
    ax.yaxis.set_major_formatter(FuncFormatter(bytes))
    if largest / smallest > 10:
        ax.yaxis.set_minor_formatter("")
    else:
        ax.yaxis.set_minor_formatter(FuncFormatter(bytes))

    # draw the graph {{{3
    ax.legend(loc='upper left')
    if svg_file:
        plt.savefig(svg_file)
    else:
        plt.show()

# print_report() {{{1
def print_report(repos, style):
    if not style:
        style = settings.get('report_style', 'compact')
    if style == 'compact':
        print_compact_report(repos)
    elif style == 'normal':
        print_normal_report(repos)
    elif style == 'tree':
        print_tree_report(repos)
    elif style in ['nt', 'nestedtext']:
        print_nestedtext_report(repos)
    elif style == 'json':
        print_json_report(repos)
    else:
        raise Error(
            "unknown style",
            "choose from compact, normal, tree, nt or nestedtext, or json",
            culprit = style
        )

# print_compact_report() {{{1
def print_compact_report(repos):
    # most compact, but has awkward config labels

    fmt = size_format
    msg_fmt = settings.get(
        'compact_format',
        '{config}: {size:{fmt}}'
    )

    # report the sizes
    for name in sorted(repos):
        repo = repos[name]
        msg = msg_fmt.format(repo=name, fmt=fmt, **repo)
        display(msg)

# print_normal_report() {{{1
def print_normal_report(repos):
    # same number of lines as compact, but a bit more verbose

    fmt = size_format
    hostname = gethostname()
    username = getusername()
    msg_fmt = settings.get(
        'normal_format',
        '{host:8} {user:8} {config:8} {size:<8.2b}  {last_create:ddd, MMM DD}'
    )

    # split config name, then sort by host, user, then config
    repos = sorted(
        (split_repo_name(name) + (repo,) for name, repo in repos.items()),
        key = lambda k: (k[2], k[1], k[0])
    )

    # report the sizes
    header = settings.get(
        'normal_header',
        'HOST     USER     CONFIG   SIZE      LAST BACK UP'
    )
    if header:
        display(header)

    for cfg, hst, usr, repo in repos:
        hst = hst or hostname
        usr = usr or username
        msg = msg_fmt.format(host=hst, user=usr, config=cfg, fmt=fmt, **repo)
        display(msg)

# as_hierarchy() {{{1
def as_hierarchy(repos, fmt, squeeze):
    hostname = gethostname()
    username = getusername()

    # split config name, then sort by host, user, then config
    repos = sorted(
        (split_repo_name(name) + (repo,) for name, repo in repos.items()),
        key = lambda k: (k[1], k[2], k[0])
    )

    # convert hierarchy levels to dictionaries
    if squeeze:
        # lowest level is a list of strings rather than a dictionary
        hierarchy = {}
        for cfg, hst, usr, repo in repos:
            hst = hst or hostname
            usr = usr or username
            if hst not in hierarchy:
                hierarchy[hst] = {}
            if usr not in hierarchy[hst]:
                hierarchy[hst][usr] = [] if squeeze else {}
            if cfg not in hierarchy[hst][usr]:
                hierarchy[hst][usr].append(f"{cfg}: {fmt(repo)}")
    else:
        hierarchy = {}
        # all levels are dictionaries, lowest level is dictionary of strings
        for cfg, hst, usr, repo in repos:
            hst = hst or hostname
            usr = usr or username
            if hst not in hierarchy:
                hierarchy[hst] = {}
            if usr not in hierarchy[hst]:
                hierarchy[hst][usr] = [] if squeeze else {}
            if cfg not in hierarchy[hst][usr]:
                hierarchy[hst][usr][cfg] = fmt(repo)

    return hierarchy

# print_tree_report() {{{1
def print_tree_report(repos):
    # longer than previous formats
    # good when there are many repos per host & user
    fields = settings.get('tree_report_fields', report_fields)

    def formatter(repo):
        to_output = {}
        for field in fields:
            value = repo[field]
            if field in size_fields:
                value = value.format(size_format)
            elif field in date_fields:
                value = value.format(date_format) if date_format else str(value)
            to_output[field] = value
        return to_output

    squeeze = fields == size_fields
    if squeeze:
        formatter = lambda r: r['size'].format(size_format)

    display(tree(as_hierarchy(repos, fmt=formatter, squeeze=squeeze)))

# print_nestedtext_report() {{{1
def print_nestedtext_report(repos):
    # same number of lines as tree, but both computer & human readable
    fields = settings.get('nestedtext_report_fields', report_fields)

    def formatter(repo):
        to_output = {}
        for field in fields:
            value = repo[field]
            if field in size_fields:
                value = value.format(nestedtext_size_format)
            elif field in date_fields:
                value = value.format(date_format) if date_format else str(value)
            to_output[field] = value
        return to_output

    display(nt.dumps(as_hierarchy(repos, fmt=formatter, squeeze=False)))

# print_json_report() {{{1
def print_json_report(repos):
    # easily computer readable, but awkward for people
    fields = settings.get('json_report_fields', report_fields)

    def formatter(repo):
        to_output = {}
        for field in fields:
            value = repo[field]
            if field in size_fields:
                value = int(value)
            elif field in date_fields:
                value = str(value)
            to_output[field] = value
        return to_output

    display(
        json.dumps(
            as_hierarchy(repos, fmt=formatter, squeeze=False),
            indent=4,
            separators=(',', ': '),
            ensure_ascii=False
        )
    )

# main() {{{1
def main():
    cmdline = docopt(__doc__, version=__version__)

    requests = cmdline['<repo>']
    if not requests:
        requests = ['']  # this gets the default config

    try:
        repos = collect_repos(requests, cmdline['--record'])

        if cmdline['--graph'] or cmdline['--svg'] or cmdline['--log-y']:
            generate_graph(repos, cmdline['--svg'], cmdline['--log-y'])
        elif not cmdline['--quiet']:
            print_report(repos, cmdline['--style'])
    except (Error, nt.NestedTextError) as e:
        e.report()
    except OSError as e:
        error(os_error(e))
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
