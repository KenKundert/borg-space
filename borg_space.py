#!/usr/bin/env python3
# description {{{1
"""
Borg Space

Reports on the current size of one or more Borg repositories managed by Emborg.

Usage:
    borg-space [--quiet] [--message <msg>] [--record] [<config>...]
    borg-space [--graph] [--svg <file>] [--log-y] [<config>...]

Options:
    -r, --record                save the result
    -q, --quiet                 do not output the size message
    -m <msg>, --message <msg>   the size message
    -g, --graph                 graph the previously recorded sizes over time
    -l, --log-y                 use a logarithmic Y-axis when graphing
    -s <file>, --svg <file>     produce plot as SVG file rather than display it

Results are saved to ~/.local/share/emborg/<config>-sizes.nt.
<msg> may contain {size}, which is replaced with the measured size, and 
{config}, which is replaced by the config name.
If no replacements are made, size is appended to the end of the message.
"""

# imports {{{1
import arrow
from appdirs import user_data_dir
from docopt import docopt
from emborg import Emborg
from inform import Error, display, error, os_error
from pathlib import Path
from quantiphy import Quantity
import json
import nestedtext as nt
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from matplotlib.ticker import FuncFormatter

# globals {{{1
data_dir = Path(user_data_dir('emborg'))
now = str(arrow.now())
Quantity.set_prefs(prec=2)
__version__ = "0.4.0"
__released__ = "2022-10-22"

# generate_graph() {{{1
def generate_graph(requests, svg_file, log_scale):
    configs = []
    if svg_file:
        matplotlib.use('SVG')

    # expand composite configs and gather the scalar configs {{{2
    for request in requests:
        with Emborg(request, emborg_opts=['no-log'], exclusive=False) as emborg:
            configs.extend(emborg.configs)

    # determine size history of each config's repository {{{2
    traces = []
    for config in configs:
        data_path = data_dir / f'{config}-size.nt'
        data = nt.load(data_path, top=dict)
        sizes = []
        dates = []
        for date, size in data.items():
            dates.append(arrow.get(date))
            sizes.append(Quantity(size, 'B').real)
        traces.append((config, Quantity(size, 'B'), dates, sizes))

    # plot the results {{{2
    # create and configure the canvas {{{3
    fig = plt.figure()
    ax = fig.add_subplot(111)
    if log_scale:
        ax.set_yscale('log')

    # configure the axis labeling {{{3
    ax.xaxis.set_major_formatter(DateFormatter('%b %g'))

    # add traces in order of last size, largest to smallest {{{3
    largest = 0
    smallest = 1e100
    for entry in sorted(traces, key=lambda d: d[1], reverse=True):
        name, last_size, dates, sizes = entry
        largest = max(largest, *sizes)
        smallest = min(smallest, *sizes)
        trace, = ax.plot_date(dates, sizes, "d-")
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
    ax.legend(loc='lower left')
    if svg_file:
        plt.savefig(svg_file)
    else:
        plt.show()

# generate_report() {{{1
def generate_report(requests, show_size, record_size, message):

    for request in requests:
        # expand composite configs {{{2
        with Emborg(request, emborg_opts=['no-log'], exclusive=False) as emborg:
            configs = emborg.configs
            if configs is None:
                raise Error(
                    'emborg is too old.',
                    codicil = "upgrade using 'pip install --user --upgrade emborg'."
                )

        # iterate through configs {{{2
        for config in configs:
            with Emborg(config, emborg_opts=['no-log'], exclusive=False) as emborg:

                # get name of latest archive {{{3
                borg = emborg.run_borg(
                    cmd = 'list',
                    args = ['--json', emborg.destination()]
                )
                response = json.loads(borg.stdout)
                try:
                    archive = response['archives'][-1]['archive']
                except IndexError:
                    raise Error('no archives available.', culprit=config)

                # get size info for latest archive {{{3
                borg = emborg.run_borg(
                    cmd = 'info',
                    args = ['--json', emborg.destination(archive)]
                )
                response = json.loads(borg.stdout)
                size = response['cache']['stats']['unique_csize']

                # record the size {{{3
                if record_size:
                    # read previously recorded sizes
                    data_path = Path(data_dir / f'{config}-size.nt')
                    try:
                        data = nt.load(data_path, top=dict)
                    except FileNotFoundError:
                        data = {}

                    # append new size
                    data[now] = size

                    # write out sizes
                    nt.dump(data, data_path)

                # report the size {{{3
                if show_size:
                    size_in_bytes = Quantity(size, 'B')
                    if not message:
                        message = '{config}: {size}'
                    msg = message.format(config=config, size=size_in_bytes)
                    if msg == message:
                        msg = f'{message}: {size_in_bytes}'
                    display(msg)

# main() {{{1
def main():
    cmdline = docopt(__doc__, version=__version__)

    requests = cmdline['<config>']
    if not requests:
        requests = ['']  # this gets the default config

    try:
        if cmdline['--graph'] or cmdline['--svg'] or cmdline['--log-y']:
            generate_graph(requests, cmdline['--svg'], cmdline['--log-y'])
        else:
            generate_report(
                requests,
                not cmdline['--quiet'],
                cmdline['--record'],
                cmdline['--message']
            )
    except (Error, nt.NestedTextError) as e:
        e.report()
    except OSError as e:
        error(os_error(e))
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
