#!/usr/bin/env python

import os
import stat
import subprocess
import sys

import pgl

DGIT_CONF = 'dgit.'
DGIT_CONF_LEN = len(DGIT_CONF)
DGITEXT_CONF = 'dgitext.'
DGITEXT_CONF_LEN = len(DGITEXT_CONF)
ALIAS_CONF = 'alias.'
ALIAS_CONF_LEN = len(ALIAS_CONF)
DEFAULT_CONF = 'defaults.'
DEFAULT_CONF_LEN = len(DEFAULT_CONF)

cmd_options = []
config = {'git-hg':False, 'hub':False, 'cmds':None}

try:
    import ghg
except ImportError:
    # If we can't import ghg, it doesn't matter if git-hg is otherwise installed,
    # we can't do any git-hg work
    config['git-hg'] = None

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
    """Find the location of git-hg and hub, if we haven't been explicitly told
    where they are
    """
    # None means we don't WANT to find the external program in question, so
    # we'll pretend we already found it so we don't ACTUALLY find it
    ghg_found = True if config['git-hg'] is None else bool(config['git-hg'])
    hub_found = True if config['hub'] is None else bool(config['hub'])

    if 'hg' in config['cmds'] and not ghg_found:
        config['git-hg'] = True
        ghg_found = True

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
    """Make a list of git's built-in commands
    """
    for f in os.listdir(pgl.config['GIT_LIBEXEC']):
        if '--' in f:
            # Skip these, since they're just additions to other git commands
            continue
        full = os.path.join(pgl.config['GIT_LIBEXEC'], f)
        if f.startswith('git-') and os.path.isfile(full) and \
            (os.stat(full).st_mode & (stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH)):
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
    elif len(options) > 0:
        pgl.die('Ambiguous command!')
    pgl.die('Can not figure out what git command to run!')

def check_git_hg_push(args):
    """Raise an exception if we're doing push in a git-hg repo to something that
    is NOT our hg remote
    """
    remotes = set([k.split('.')[1] for k in pgl.config if k.startswith('remote.')])
    for a in args:
        if a in remotes and a != 'hg':
            raise Exception, 'Prevent us from doing something stupid'

def handle_git_hg(cmd, pos, args):
    """Return a modified argument list if we're doing an operation on a git-hg
    repo. For example, cloning an hg repo using the special URL syntax
      git clone hg+http://hg.example.com/repo
    Which passes us the args list
      ['clone', 'hg+http://hg.example.com/repo']
    Would return the new list
      ['hg', 'clone', 'http://hg.example.com/repo']

    Similarly, running a fetch in an hg repo (that does not fetch from a non-hg
    remote) like
      git fetch
    Which passes us the args list
      ['fetch']
    Would return the new list
      ['hg', 'fetch']
    """
    offset = 0
    if cmd in ('clone', 'fetch', 'pull', 'push'):
        if cmd == 'clone':
            urlpos = None
            for i, a in enumerate(args):
                if a.startswith('hg+'):
                    urlpos = i
            if urlpos is not None:
                # This means we've found an hg-special URL, so we need to
                # massage this command into a git-hg command
                args[urlpos] = args[urlpos][3:]
                args.insert(pos, 'hg')
                offset = 1
        else:
            try:
                ghg.include_hg_setup()
                ghg.ensure_is_ghg()
                if cmd in ('fetch', 'pull') and len(args) != 1:
                    # Someone's fetching or pulling from NOT hg
                    raise Exception, 'This just breaks us out before we do bad'
                if cmd == 'push':
                    check_git_hg_push(args)

                # If we get here, we're reasonably confident we're operating on
                # the actual HG remote instead of some random other git remote,
                # so make go on that!
                args.insert(pos, 'hg')
                offset = 1
            except:
                # This isn't a Git-HG repo, we're communicating with a non-hg
                # remote, or there was some error figuring out the git-hg setup
                # for the current dir, so we just continue on with our original
                # command and args, trusting the REAL git to give us a proper
                # error message if necessary
                pass

    return args, offset

@pgl.main
def main():
    defaults = {}

    # Find out if we're configured to handle git-hg and/or hub
    if DGIT_CONF + 'githg' in pgl.config and config['git-hg'] is not None:
        config['git-hg'] = pgl.config[DGIT_CONF + 'githg']
    if DGIT_CONF + 'hub' in pgl.config:
        val = pgl.config[DGIT_CONF + 'hub']
        if val.lower() in ('off', '0', 'false'):
            config['hub'] = None
        else:
            config['hub'] = val

    for k, v in pgl.config.iteritems():
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

    # Make sure git gets the full command name
    args[cmdpos] = cmd

    # Find out where git-hg and hub are, if necessary
    locate_externals()

    if config['git-hg']:
        # Offset will adjust our mangling of the arg list below for the addition
        # of "hg" into the list, if necessary
        args, offset = handle_git_hg(cmd, cmdpos, args)

    # Now update our argument list with any defaults we may have
    argdefaults = config['cmds'].get(cmd, None)
    if argdefaults:
        # Always put the argument defaults in just after the command
        args = args[:cmdpos + 1 + offset] + argdefaults + \
            args[cmdpos + 1 + offset:]

    # Figure out which binary we're to execute next, and execute it
    if config['hub']:
        exe = config['hub']
    else:
        exe = 'git'
    args = [exe] + args
    os.execvp(exe, args)

    # Crap...
    pgl.die('Failed to execvp %s!' % (exe,))
