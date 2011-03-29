#!/usr/bin/env python

import os
import stat
import subprocess
import sys

DGIT_CONF = 'dgit.'
DGIT_CONF_LEN = len(DGIT_CONF)
ALIAS_CONF = 'alias.'
ALIAS_CONF_LEN = len(ALIAS_CONF)
DEFAULT_CONF = 'defaults.'
DEFAULT_CONF_LEN = len(DEFAULT_CONF)

def is_exe(fname):
    """Determine if a file exists, and, if so, if it's executable by our user
    """
    uid = os.geteuid()
    if sys.platform == 'darwin':
        # HACK WARNING - at least on my OS X install, os.getgroups() causes
        # python to segfault, so we do this crazy thing instead to figure out
        # what groups the current user is a member of
        gid = subprocess.Popen(['id', '-G'], stdout=subprocess.PIPE)
        groups = set(gid.stdout.read().split())
        gid.wait()
    else:
        groups = set(os.getgroups())

    if os.path.exists(fname):
        while os.path.islink(fname):
            dname = os.path.dirname(fname)
            fname = os.path.readlink(fname)
            if not os.path.isabs(fname):
                fname = os.path.abspath(os.path.join(dname, fname))
        if not os.path.exists(fname):
            # We got a dead link
            return False
        s = os.stat(fname)
        if s.st_uid == uid:
            flags = stat.S_IRUSR | stat.S_IXUSR
        elif s.st_gid in groups:
            flags = stat.S_IRGRP | stat.S_IXGRP
        else:
            flags = stat.S_IROTH | stat.S_IXOTH
        if s.st_mode & flags:
            return True

    return False

def locate_externals(config):
    """Find the location of git-hg and hub, if we haven't been explicitly told
    where they are
    """
    ghg_found = bool(config['git-hg'])
    # Hub is a special case - 'None' means we don't WANT to find it, so if
    # that's its value, we'll treat it as already found
    hub_found = True if config['hub'] is None else bool(config['hub'])

    if ghg_found and hub_found:
        # Hey, look! We're done without even really starting!
        return

    path = os.getenv('PATH')
    path = path.split(os.pathsep)
    for d in path:
        ghg = os.path.join(d, 'git-hg')
        hub = os.path.join(d, 'hub')
        if not ghg_found and is_exe(ghg):
            config['git-hg'] = ghg
            ghg_found = True
        if not hub_found and is_exe(hub):
            config['hub'] = hub
            hub_found = True
        if ghg_found and hub_found:
            # Finally!
            return

def load_git_commands():
    # TODO
    pass

def handle_git_hg():
    # TODO
    pass

if __name__ == '__main__':
    cmd_options = []
    config = {'git-hg':False, 'hub':False, 'cmds':None}

    git_config = subprocess.Popen(['git', 'config', '-l'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    defaults = {}
    for line in git_config.stdout:
        key, val = line.strip().split('=', 1)
        key = key.strip()
        val = val.strip()
        if key.startswith(DGIT_CONF):
            subkey = key[DGIT_CONF_LEN:]
            if subkey == 'githg':
                config['git-hg'] = val
            elif subkey == 'hub':
                if val.lower() in ('off', '0', 'false'):
                    config['hub'] = None
                else:
                    config['hub'] = val
        elif key.startswith(ALIAS_CONF):
            cmd_options.append(key[ALIAS_CONF_LEN:])
        elif key.startswith(DEFAULT_CONF):
            defaults[key[DEFAULT_CONF_LEN:]] = val.split()
    git_config.wait()

    # Load the list of built-in git commands, add them to our list of all
    # available commands (built-in and aliases), and finally sort the list
    cmd_options += load_git_commands()
    cmd_options.sort(key=lambda x: x.lower())
    config['cmds'] = dict.fromkeys(cmd_options, [])

    # See if we're supposed to actually use our defaults, or just provide the
    # other services. Load the defaults if necessary
    if sys.argv[1] != '--nodefaults':
        config['cmds'].update(defaults)
        gitargs = sys.argv[1:]
    else:
        gitargs = sys.argv[2:]

    # Find out where git-hg and hub are, if necessary
    locate_externals(config)

    # Figure out which git command we're running
    cmd, dargs = get_git_command(config['cmds'])

    # TODO

    sys.exit(0)
