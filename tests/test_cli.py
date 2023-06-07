# Test Borg Space
# TO check:
#     allows running without settings file
#     disallow unknown fields in repositories
#     allow running without repositories setting

# IMPORTS {{{1
import pytest, os
from parametrize_from_file import parametrize, defaults
from pytest_tmp_files import tmp_file_type
from functools import partial
from quantiphy import UnitConversion, Quantity
from re_assert import Matches
from shlib import Run, ln, lsf, rm
from voluptuous import Schema, Optional, Required, Any
import re
import os
import pwd
import socket

# INITIALIZE {{{1
hostname = socket.gethostname().split('.')[0]
    # version of the hostname (the hostname without any domain name)
username = pwd.getpwuid(os.getuid()).pw_name


# Adapt parametrize_for_file to read dictionary rather than list {{{2
def name_from_dict_keys(cases):
    return [{**v, 'name': k} for k,v in cases.items()]

parametrize = partial(parametrize, preprocess=name_from_dict_keys)


# Schema for test cases {{{2
def to_int(arg):
    return int(arg)

borg_space_schema = Schema({
    Required('name'): str,  # this field is promoted to key by above code
    Optional('args', default=''): Any(str, list),
    Optional('stdout', default="^$"): str,
    Optional('stderr', default="^$"): str,
    Optional('status', default=0): to_int,
    Optional('env', default={}): dict,
    Optional('tmp_files', default={}): {str:Any(str, {str:str})},
}, required=True)#

# Time Conversions {{{2
UnitConversion("s", "sec second seconds")
UnitConversion("s", "m min minute minutes", 60)
UnitConversion("s", "h hr hour hours", 60*60)
UnitConversion("s", "d day days", 24*60*60)
UnitConversion("s", "w W week weeks", 7*24*60*60)
UnitConversion("s", "M month months", 30*24*60*60)
UnitConversion("s", "y Y year years", 365*24*60*60)
Quantity.set_prefs(ignore_sf=True)

# substitutions {{{2
def sub_local_names(text):
    return text.replace('❬HOST❭', hostname).replace('❬USER❭', username)

# process temp file parametrization {{{2
@tmp_file_type('parametrized')
def make_parameterized_file(path, meta):
    content = sub_local_names(meta['content'])
    # still need to do date substitutions
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)

# RUN BORG-SPACE{{{1
def check_command(name, args, env, stdout, stderr, status, home):
    env = {
        **os.environ,
        '_BORG_SPACE__OVERRIDE_HOME_FOR_TESTING_': home,
        **env,
    }
    cmd = './bs ' + sub_local_names(args)
    stderr = sub_local_names(stderr)
    stdout = sub_local_names(stdout)

    print(f"Running: {name}")
    process = Run(cmd, "sOEW*", env=env)
    Matches(stderr, flags=re.DOTALL).assert_matches(process.stderr)
    Matches(stdout, flags=re.DOTALL).assert_matches(process.stdout)
    assert status == process.status


# TESTS {{{1
@parametrize(
    schema = borg_space_schema,
    indirect = ['tmp_files'],
)
def test_main(tmp_files, name, args, env, stdout, stderr, status):
    check_command(name, args, env, stdout, stderr, status, home=tmp_files)
