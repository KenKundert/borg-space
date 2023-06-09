# Process settings file

# IMPORTS {{{1
from appdirs import user_config_dir
from inform import (
    Error, conjoin, error, fatal, full_stop,
    is_str, is_mapping, is_collection, plural, os_error, terminate
)
from quantiphy import Quantity
from shlib import to_path, Run, set_prefs
from voluptuous import Schema, Invalid, MultipleInvalid
import arrow
import getpass
import nestedtext as nt
import os
import pwd
import socket


# TESTING MODS {{{1
# this code overrides the home directory (only used for testing)
new_home = os.environ.get('_BORG_SPACE__OVERRIDE_HOME_FOR_TESTING_')
if new_home:  # pragma: no cover
    true_home = os.environ['HOME'].rstrip('/') + '/'
    unaltered_to_path = to_path
    def to_path(arg):
        full_path = unaltered_to_path(arg).resolve()
        as_str = str(full_path)
        if as_str.startswith(true_home):
            full_path = unaltered_to_path(new_home, as_str[len(true_home):])
        return full_path

# GLOBALS {{{1
set_prefs(use_inform=True)
settings_file = to_path(user_config_dir('borg-space')) / 'settings.nt'
voluptuous_error_msg_mappings = {
    "extra keys not allowed": ("unknown key", "key"),
    "expected a dictionary": ("expected key:value pair", "value"),
}
hostname = socket.gethostname().split('.')[0]
    # version of the hostname (the hostname without any domain name)
username = pwd.getpwuid(os.getuid()).pw_name


# REPOSITORY {{{1
# Repository class {{{2
class Repository:
    def __init__(self, spec, name=None):
        prefix, _, user = spec.partition('~')
        config, _, host = prefix.partition('@')
        if not config:
            raise Error("spec is missing Emborg config name.", culprit=spec)
        if not name:
            name = spec

        self.spec = spec
        self.name = name
        self.config = a_name(config)
        self.host = a_name(host) or hostname
        self.user = a_name(user) or username
        self.latest = None

    def __str__(self):
        return f"{self.config}@{self.host}~{self.user}"

    def __repr__(self):
        return f'{self.__class__.__name__}("{str(self)}")'

    def __getitem__(self, key):
        if self.latest and key in self.latest:
            return self.latest[key]
        return self.__dict__[key]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def as_dict(self):
        info = dict(
            name = self.name,
            spec = self.spec,
            config = self.config,
            host = self.host,
            user = self.user,
            full_spec = str(self)
        )
        info.update(self.latest)
        return info

    def get_path(self):
        user = self.user if self.user else getpass.getuser()
        config = self.config
        assert config
        path = f"~{user}/.local/share/emborg/{config}.latest.nt"
        return (self.host, path)

    def get_latest(self):
        if self.latest:
            return self.latest
        host, path = self.get_path()
        if host != hostname:
            cmd = ['ssh', host, f"cat {path}"]
            ssh = Run(cmd, modes='sOEW')
            content = ssh.stdout
        else:
            try:
                content = to_path(path).read_text()
            except FileNotFoundError:
                raise Error('unknown repository.', culprit=str(self))
        raw_data = nt.loads(content)
        self.latest = data = {}
        if 'repository size' in raw_data:
            data['size'] = Quantity(raw_data['repository size'], 'B')
        if 'create last run' in raw_data:
            data['last_create'] = arrow.get(raw_data['create last run'])
        if 'prune last run' in raw_data:
            data['last_prune'] = arrow.get(raw_data['prune last run'])
        if 'compact last run' in raw_data:
            data['last_compact'] = arrow.get(raw_data['compact last run'])
        if 'last_prune' in data and 'last_compact' in data:
            data['last_squeeze'] = max(data['last_prune'], data['last_compact'])
        return data

# get_repos() {{{2
def get_repos(spec):
    if not spec:
        spec = settings.get('default_repository')
    if not spec:
        raise Error('there is no default repository.')

    try:
        children = repositories[spec]
    except (TypeError, KeyError):
        # not found in repositories specified in settings file.
        # see if it exists on local machine
        children = [Repository(spec)]

    results = {}
    for child in children:
        host, path = child.get_path()
        name = str(child)
        try:
            child.get_latest()
            results[name] = child
        except Error as e:
            e.report(culprit=name)
        except OSError as e:
            error(os_error(e), culprit=name)
    return results


# SCHEMA {{{1
# to_snake_case() {{{2
def to_snake_case(text):
    return '_'.join(text.lower().split())

# normalize_key() {{{2
def normalize_key(key, parent_keys):
    if len(parent_keys) == 1:
        return key
    return to_snake_case(key.replace('_', ' '))

# to_list() {{{2
def to_list(args):
    if is_str(args):
        args = args.split()
    if is_mapping(args):
        raise Invalid(f"{args}: expected list or string")
    return args

# a_name() {{{2
def a_name(arg):
    # names are expected to be identifiers except that dashes are allowed
    if not arg:
        return arg
    if not is_str(arg):
        raise Invalid("expected string")
    cleaned = arg.replace('-', '0')
    if not cleaned.isidentifier():
        raise Invalid(f"{arg}: expected a name")
    return arg

# a_spec() {{{2
def a_spec(arg):
    if is_str(arg):
        return arg
    if is_mapping(arg):
        unknown_keys = arg.keys() - set(['config', 'host', 'user'])
        if unknown_keys:
            raise Invalid(f"unknown {plural(unknown_keys):key}: {conjoin(unknown_keys)}.")
        if 'config' not in arg:
            raise Invalid("config is a required key.")
        spec = arg.get('config')
        if arg.get('host'):
            spec = f"{spec}@{arg.get('host')}"
        if arg.get('user'):
            spec = f"{spec}~{arg.get('user')}"
        return spec
    raise Invalid("expected a specification")

# to_specs() {{{2
def to_specs(arg):
    if is_str(arg):
        return [a_spec(r) for r in arg.split()]
    if is_mapping(arg):
        unknown_keys = arg.keys() - set(['config', 'host', 'user'])
        if unknown_keys:
            raise Invalid(f"unknown {plural(unknown_keys):key}: {conjoin(unknown_keys)}.")
        return [a_spec(arg)]
    if is_collection(arg):
        return [a_spec(r) for r in arg]
    raise Invalid("expected a repository specification")

# validate_settings {{{2
validate_settings = Schema({
    'repositories': {a_name: to_specs},
    'default_repository': str,
    'report_style': str,
    'compact_format': str,
    'table_format': str,
    'table_header': str,
    'report_fields': to_list,
    'tree_report_fields': to_list,
    'nestedtext_report_fields': to_list,
    'json_report_fields': to_list,
    'size_format': str,
    'date_format': str,
})

# READ SETTINGS FILE {{{1
try:
    # load tables from file
    keymap = {}
    settings = nt.load(
        settings_file,
        top = 'dict',
        normalize_key = normalize_key,
        keymap = keymap,
    )

    settings = validate_settings(settings)
    specifications = settings.get('repositories', {})

    # convert from specifications to Repository objects
    repositories = {}
    for name, specs in specifications.items():
        if specs:
            repositories[name] = []
            alias = name if len(specs) <= 1 else None
            for spec in specs:
                if spec in repositories and spec != name:
                    # this is a known (previously defined) repository
                    repositories[name].extend(repositories[spec])
                else:
                    repositories[name].append(Repository(spec, alias))
        else:
            repositories[name] = [Repository(name)]

except nt.NestedTextError as e:
    e.terminate()
except FileNotFoundError:
    settings = {}
    repositories = {}
except OSError as e:
    fatal(os_error(e), culprit=settings_file)
except MultipleInvalid as e:  # report schema violations
    for err in e.errors:
        msg, flag = voluptuous_error_msg_mappings.get(
            err.msg, (err.msg, 'value')
        )
        loc = keymap.get(tuple(err.path))
        codicil = loc.as_line(flag) if loc else None
        keys = nt.join_keys(err.path, keymap=keymap)
        error(
            full_stop(msg),
            culprit = (settings_file, keys),
            codicil = codicil
        )
    terminate()
