from appdirs import user_config_dir
from inform import (
    Error, error, fatal, full_stop, is_str, is_mapping, os_error, terminate
)
from quantiphy import Quantity
from voluptuous import Schema, Required, Invalid, MultipleInvalid
import nestedtext as nt
import arrow
import getpass
from shlib import to_path, Run, set_prefs
set_prefs(use_inform=True)

settings_file = to_path(user_config_dir('borg-space')) / 'settings.nt'

voluptuous_error_msg_mappings = {
    "extra keys not allowed": ("unknown key", "key"),
    "expected a dictionary": ("expected key-value pair", "value"),
}

class Repository:
    def __init__(self, config=None, host=None, user=None):
        self.config = config
        self.host = host
        self.user = user
        self.latest = None

    def __str__(self):
        name = self.__class__.__name__
        args = ', '.join(f'{k}={v}' for k, v in self.__dict__.items() if v)
        return f"{name}({args})"

    __repr__ = __str__

    def get_path(self, key=None):
        user = self.user if self.user else getpass.getuser()
        config = self.config if self.config else key
        path = f"~{user}/.local/share/emborg/{config}.latest.nt"
        return (self.host, path)

    def get_name(self, key=None):
        name = self.config if self.config else key
        if self.host:
            name += '@' + self.host
        if self.user:
            name += '~' + self.user
        return name

    def get_repo(self):
        if self.latest:
            return self.latest
        path = self.get_path(None)[1]
        if self.host:
            cmd = ['ssh', self.host, f"cat {path}"]
            ssh = Run(cmd, modes='sOEW')
            content = ssh.stdout
        else:
            try:
                content = to_path(path).read_text()
            except FileNotFoundError:
                raise Error('unknown configuration.', culprit=self.get_name(None))
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

def to_snake_case(text):
    return '_'.join(text.lower().split())

def normalize_key(key, parent_keys):
    if len(parent_keys) == 1:
        return key
    return to_snake_case(key.replace('_', ' '))

def must_be_identifier(arg):
    if not arg:
        return arg
    if not is_str(arg):
        raise Invalid("expected string")
    if arg and not arg.isidentifier():
        raise Invalid(f"{arg}: expected identifier")
    return arg

def as_list(args):
    if is_str(args):
        args = args.split()
    if is_mapping(args):
        raise Invalid(f"{args}: expected list or string")
    return args

def split_repo_name(arg):
    # extract components from: config@host~user
    try:
        config, _, user = arg.partition('~')
        config, _, host = config.partition('@')
        return (
            must_be_identifier(config),
            must_be_identifier(host),
            must_be_identifier(user)
        )
    except AttributeError:
        raise ValueError("expected string")

def as_repo(arg):
    config, host, user = split_repo_name(arg)
    return Repository(config, host, user)

def as_list_of_repos(repos):
    if is_str(repos):
        repos = repos.split()
    if is_mapping(repos):
        return must_be_a_repo(repos)
    return [as_repo(repo) for repo in repos]

def must_be_a_repo(repo):
    if is_str(repo):
        return [as_repo(repo)]
    if is_mapping(repo):
        if 'children' in repo:
            children = as_list_of_repos(repo.pop('children'))
            if repo:
                raise Invalid("children cannot be used with other fields")
            return children
        must_be_identifier(repo.get('config'))
        must_be_identifier(repo.get('host'))
        must_be_identifier(repo.get('user'))
        return [Repository(**repo)]
    raise Invalid("must me a string or a dictionary")

validate_settings = Schema({
    Required('repositories'): {str: must_be_a_repo},
    'default_repository': str,
    'report_style': str,
    'compact_format': str,
    'normal_format': str,
    'normal_header': str,
    'report_fields': as_list,
    'tree_report_fields': as_list,
    'nestedtext_report_fields': as_list,
    'nestedtext_size_format': str,
    'json_report_fields': as_list,
    'size_format': str,
    'date_format': str,
})

try:
    # load tables from file
    keymap = {}
    settings = nt.load(
        settings_file,
        top = 'dict',
        normalize_key = normalize_key,
        keymap = keymap,
    )

    # check structure of the file contends
    settings = validate_settings(settings)
    repositories = settings['repositories']

except nt.NestedTextError as e:
    e.terminate()
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
    terminate("borg-space: terminated due to previously reported errors.")

def gather(repo):
    try:
        name = repo.get_name(None)
    except TypeError:
        return [repo]
    if name.isidentifier() and name in repositories:
        return repositories[name]
    return [repo]

def get_repos(repo):
    if not repo:
        repo = settings.get('default_repository')
    if not repo:
        raise Error('there is no default repository.')

    try:
        children = repositories[repo]
    except KeyError:
        # not found in repositories specified in settings file.
        # see if it exist on local machine
        try:
            children = [as_repo(repo)]
        except Invalid as e:
            raise Error(str(e))

    results = {}

    to_process = []
    for child in children:
        to_process.extend(gather(child))

    for child in to_process:
        host, path = child.get_path(repo)
        name = child.get_name(repo)
        try:
            results[name] = child.get_repo()
        except Error as e:
            e.report(culprit=name)
        except OSError as e:
            error(os_error(e), culprit=name)
    return results
