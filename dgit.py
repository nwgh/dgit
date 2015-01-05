#!/usr/bin/env python

import os
import stat
import subprocess
import sys


DGIT_CONF = 'dgit.'
DGIT_CONF_LEN = len(DGIT_CONF)
DGITEXT_CONF = 'dgitext.'
DGITEXT_CONF_LEN = len(DGITEXT_CONF)
ALIAS_CONF = 'alias.'
ALIAS_CONF_LEN = len(ALIAS_CONF)
DEFAULT_CONF = 'defaults.'
DEFAULT_CONF_LEN = len(DEFAULT_CONF)


cmd_options = []
config = {'hub': False, 'cmds': None}


git_libexec = None
git_config = {}


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


def locate_externals():
    """Find the location of hub, if we haven't been explicitly told where they
    are
    """
    # None means we don't WANT to find the external program in question, so
    # we'll pretend we already found it so we don't ACTUALLY find it
    hub_found = True if config['hub'] is None else bool(config['hub'])

    if hub_found:
        # Hey, look! We're done without even really starting!
        return

    path = os.getenv('PATH')
    path = path.split(os.pathsep)
    for d in path:
        hub_exe = os.path.join(d, 'hub')
        if not hub_found and is_exe(hub_exe):
            config['hub'] = hub_exe
            hub_found = True
        if hub_found:
            # Finally!
            return


def is_executable_git_command(f):
    """Return true if this git command is executable like we expect, otherwise
    return false
    """
    return os.path.isfile(f) and \
        (os.stat(f).st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))


def load_git_commands():
    """Make a list of git's built-in commands
    """
    for f in os.listdir(git_libexec):
        if '--' in f:
            # Skip these, since they're just additions to other git commands
            continue
        full = os.path.join(git_libexec, f)
        if f.startswith('git-') and is_executable_git_command(full):
            cmd_options.append(f[4:])


def get_git_command(args):
    """Figure out which git command we've been told to run
    """
    options = []
    for i, a in enumerate(args):
        if a.startswith('-'):
            continue
        if a in config['cmds']:
            return a, i
        options.extend([(c, i) for c in config['cmds'] if c.startswith(a)])

    if len(options) == 1:
        return options[0]

    # We'll rely on git to blow up for us
    return None, None


def prepend_to_path(path, item):
    """Prepend <item> to the path variable <path>. Returns a new string
    """
    if not path:
        return item
    return os.pathsep.join([item, path])


def main():
    global git_libexec
    global git_config

    defaults = {}

    # Make sure we don't blow up if we're called bare
    if len(sys.argv) == 1:
        os.execvp('git', ['git'])

    # Get all the config we need from git
    gitexec = subprocess.Popen(['git', '--exec-path'], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    gitexec.wait()
    git_libexec = gitexec.stdout.readlines()[0].strip()

    gitvar = subprocess.Popen(['git', 'var', '-l'], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
    gitvar.wait()
    for line in gitvar.stdout:
        k, v = line.strip().split('=', 1)
        if v == 'true':
            v = True
        elif v == 'false':
            v = False
        else:
            try:
                v = int(v)
            except ValueError:
                pass
        git_config[k] = v

    # Find out if we're configured to handle hub
    if DGIT_CONF + 'hub' in git_config:
        val = git_config[DGIT_CONF + 'hub']
        if val.lower() in ('off', '0', 'false'):
            config['hub'] = None
        else:
            config['hub'] = val

    for k, v in git_config.iteritems():
        if k.startswith(ALIAS_CONF):
            cmd_options.append(k[ALIAS_CONF_LEN:])
        elif k.startswith(DGITEXT_CONF):
            cmd_options.append(k[DGITEXT_CONF_LEN:])
        elif k.startswith(DEFAULT_CONF):
            defaults[k[DEFAULT_CONF_LEN:]] = v.split()

    # Load the list of built-in git commands, add them to our list of all
    # available commands (built-in and aliases), and finally sort the list
    load_git_commands()
    cmd_options.sort(key=lambda x: x.lower())
    config['cmds'] = dict.fromkeys(cmd_options, [])

    # See if we're supposed to actually use our defaults, or just provide the
    # other services. Load the defaults if necessary
    if sys.argv[1] != '--nodefaults':
        config['cmds'].update(defaults)
        args = sys.argv[1:]
    else:
        args = sys.argv[2:]

    # Figure out which git command we're running
    cmd, cmdpos = get_git_command(args)

    if cmd is not None:
        # Make sure git gets the full command name
        args[cmdpos] = cmd

        # Find out where hub is, if necessary
        locate_externals()

        # Now update our argument list with any defaults we may have
        argdefaults = config['cmds'].get(cmd, None)
        if argdefaults:
            # Always put the argument defaults in just after the command
            args = args[:cmdpos + 1] + argdefaults + \
                args[cmdpos + 1:]

    git_remote_hg = git_config.get(DGIT_CONF + 'git-remote-hg', None)
    if git_remote_hg:
        oldpath = os.environ.get('PATH', None)
        os.environ['PATH'] = prepend_to_path(oldpath, git_remote_hg)

    pypath = git_config.get(DGIT_CONF + 'pythonpath', None)
    if pypath:
        oldpypath = os.environ.get('PYTHONPATH', None)
        os.environ['PYTHONPATH'] = prepend_to_path(oldpypath, pypath)

    # Figure out which binary we're to execute next, and execute it
    if config['hub']:
        exe = config['hub']
    else:
        exe = 'git'
    args = [exe] + args
    os.execvp(exe, args)

    # Crap...
    sys.stderr.write('Failed to execvp %s!\n' % (exe,))
    sys.exit(1)

if __name__ == '__main__':
    main()
