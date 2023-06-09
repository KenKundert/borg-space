#!/usr/bin/env python3
# description {{{1
"""
Borg Space

Reports on the current size of one or more Borg repositories managed by Emborg.

Usage:
    borg-space [--quiet] [--style <style>] [--record] [<spec>...]
    borg-space [--graph] [--svg <file>] [--log-y] [--record] [<spec>...]

Options:
    -r, --record                 save the result
    -q, --quiet                  do not output the size message
    -s <style>, --style <style>  the report style
                                 choose from compact, table, tree, nt, json
    -g, --graph                  graph the previously recorded sizes over time
    -l, --log-y                  use a logarithmic Y-axis when graphing
    -S <file>, --svg <file>      produce plot as SVG file rather than display it

Repository specs take the form ❬name❭ or ❬config❭[@❬host❭][~❬user❭]. Items in
brackets are optional and ❬name❭ is the name given for a repository the
repositories setting.

The available styles are compact, table, tree, nt or nestedtext, or json.
If you specify something other than the these, what you give is taken to be a
compact format specification.

Results are saved to ~/.local/share/borg-space/<full-spec>.nt.
Settings are held in ~/.config/borg-space/settings.nt.
"""

# imports {{{1
from .config import settings, get_repos
from .trees import tree
import arrow
from appdirs import user_data_dir
from docopt import docopt
from inform import Error, display, error, os_error, warn
from pathlib import Path
from quantiphy import Quantity
import json
import nestedtext as nt
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.dates import AutoDateFormatter, AutoDateLocator
from matplotlib.ticker import FuncFormatter

# globals {{{1
data_dir = Path(user_data_dir('borg-space'))
now = str(arrow.now())
Quantity.set_prefs(prec='full')
__version__ = "2.1"
__released__ = "2023-06-09"
date_format = settings.get('date_format', 'D MMMM YYYY')
size_format = settings.get('size_format', '.2b')
nestedtext_size_format = settings.get('nestedtext_size_format', size_format)
size_fields = ['size',]  # must contain only one value
date_fields = ['last_create', 'last_prune', 'last_compact', 'last_squeeze']
all_fields = size_fields + date_fields
report_fields = settings.get('report_fields', size_fields)
not_available = "⟪not available⟫"

# collect_repos() {{{1
def collect_repos(requests, record_size):
    repos = {}
    for request in requests:
        new_repos = get_repos(request)
        repos.update(new_repos)

    # record the size if requested {{{3
    if record_size:
        for name, repo in repos.items():

            # read previously recorded sizes
            data_path = Path(data_dir / f'{name}.nt')
            try:
                data = nt.load(data_path, top=dict)
            except FileNotFoundError:
                data_path.parent.mkdir(parents=True, exist_ok=True)
                data = {}

            latest = repo.get_latest()
            try:
                # append new size
                data[now] = latest['size'].fixed()

                # write out sizes
                nt.dump(data, data_path)
            except KeyError:
                warn('size not found, not recording.', culprit=name)

    return repos

# formatter() {{{1
def formatter(repo, fields, missing):
    # formats the values of a repository field

    def format(value, format):
        if value is None:
            return missing
        if not format:
            return str(value)
        return value.format(format)

    to_output = {}
    for field in fields:
        value = repo.get(field)
        if field in size_fields:
            value = format(value, size_format)
        elif field in date_fields:
            value = format(value, date_format)
        to_output[field.replace('_', ' ')] = value
    if len(to_output) == 1:
        # output as a scalar if there is only one value
        to_output = next(iter(to_output.values()))
    return to_output

# generate_graph() {{{1
def generate_graph(repos, svg_file, log_scale):
    if svg_file:
        matplotlib.use('SVG')

    # determine size history of each config's repository {{{2
    traces = []
    for name in repos:
        data_path = data_dir / f'{name}.nt'
        try:
            data = nt.load(data_path, top=dict)
        except OSError as e:
            raise Error(
                os_error(e),
                codicil="No history is available to plot, have you run with --record?"
            )
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
        trace.set_label(f'{name} ({last_size:{size_format}})')

    # use SI scale factors on Y-axis
    def bytes(value, pos=None):
        return Quantity(value, 'B').render()
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
        print_compact_report(repos, None)
    elif style == 'table':
        print_table_report(repos)
    elif style == 'tree':
        print_tree_report(repos)
    elif style in ['nt', 'nestedtext']:
        print_nestedtext_report(repos)
    elif style == 'json':
        print_json_report(repos)
    else:
        print_compact_report(repos, style)

# print_compact_report() {{{1
def print_compact_report(repos, style):
    # most compact, but has awkward config labels

    fmt = size_format
    if style:
        msg_fmt = style
    else:
        msg_fmt = settings.get('compact_format', '{name}: {size:{fmt}}')

    # report the sizes
    for name in sorted(repos):
        repo = repos[name]
        try:
            msg = msg_fmt.format(fmt=fmt, **repo.as_dict())
            display(msg)
        except KeyError as e:
            warn('not available.', culprit=(name, e))

# print_table_report() {{{1
def print_table_report(repos):
    # same number of lines as compact, but a bit more verbose

    fmt = size_format
    msg_fmt = settings.get(
        'table_format',
        '{host:8} {user:8} {config:8} {size:<8.2b}  {last_create:ddd, MMM DD}'
    )

    # report the sizes
    header = settings.get(
        'table_header',
        'HOST     USER     CONFIG   SIZE      LAST BACK UP'
    )
    if header:
        display(header)

    for name in sorted(repos):
        repo = repos[name]
        try:
            msg = msg_fmt.format(fmt=fmt, **repo.as_dict())
            display(msg)
        except KeyError as e:
            warn('not available.', culprit=(name, e))

# as_hierarchy() {{{1
def as_hierarchy(repos, fmt, fields, missing):
    # convert hierarchy levels to dictionaries
    hierarchy = {}
    # all levels are dictionaries, lowest level is dictionary of strings
    for name in sorted(repos):
        repo = repos[name]
        if repo.host not in hierarchy:
            hierarchy[repo.host] = {}
        if repo.user not in hierarchy[repo.host]:
            hierarchy[repo.host][repo.user] = {}
        if repo.config not in hierarchy[repo.host][repo.user]:
            hierarchy[repo.host][repo.user][repo.config] = fmt(repo, fields, missing)
    return hierarchy

# print_tree_report() {{{1
def print_tree_report(repos):
    # longer than previous formats
    # good when there are many repos per host & user
    fields = settings.get('tree_report_fields', report_fields)

    display(
        tree(
            as_hierarchy(
                repos,
                fmt = formatter,
                fields = fields,
                missing = not_available,
            )
        )
    )

# print_nestedtext_report() {{{1
def print_nestedtext_report(repos):
    # same number of lines as tree, but both computer & human readable
    fields = settings.get('nestedtext_report_fields', report_fields)

    display(
        nt.dumps(
            as_hierarchy(
                repos,
                fmt = formatter,
                fields = fields,
                missing = not_available,
            )
        )
    )

# print_json_report() {{{1
def print_json_report(repos):
    # easily computer readable, but awkward for people
    fields = settings.get('json_report_fields', all_fields)

    def formatter(repo, fields, missing):
        to_output = {}
        info = repo.as_dict()
        for field in fields:
            value = info.get(field)
            if value is None:
                value = missing
            elif field in size_fields:
                value = int(value)
            elif field in date_fields:
                value = str(value)
            to_output[field] = value
        return to_output

    display(
        json.dumps(
            as_hierarchy(
                repos,
                fmt = formatter,
                fields = fields,
                missing = None
            ),
            indent = 4,
            separators = (',', ': '),
            ensure_ascii = False
        )
    )

# main() {{{1
def main():
    cmdline = docopt(__doc__, version=__version__)

    requests = cmdline['<spec>']
    if not requests:
        requests = ['']  # this gets the default config

    try:
        repos = collect_repos(requests, cmdline['--record'])
        if repos:
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
