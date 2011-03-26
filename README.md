WHAT IS DGIT?
=============

`dgit` (pronounced "dig it", as in "Is this software awesome or what?" "Yeah, I
dig it") is a wrapper for `git` that adds the ability to configure default
arguments for `git`'s built-in commands.

THAT SOUNDS AWESOME! HOW DO I GET DGIT?
=======================================

You've come to the right place, young grasshopper. You can download it from
github (https://github.com/todesschaf/dgit).

WHAT DO I DO THEN?
==================

install dgit.py from this source directory somewhere in your `$PATH`, then do:

    alias git=dgit

for you people who use a sane shell, or:

    alias git dgit

for you wackjobs who use \*csh.

If you don't feel like "overwriting" your real `git` with `dgit` by using an
alias, `dgit` will work just fine withouth being aliased. The rest of this
README assumes you're using the alias, though.

After that, just use `git` the way you normally would. If you have `git-hg`
installed, as well, you can do things like:

    git clone hg+http://hg.example.com/examplerepo

and:

    git fetch # (in a git-hg repo)

and `dgit` will Do The Right Thing.

If you use `hub` (https://github.com/defunkt/hub) `dgit` can also be configured
to use that.

HOW DO I CONFIGURE DGIT?
========================

Why, through `gitconfig`, of course! There are two sections that are relevant to
`dgit` (though neither are required). The first is the `[dgit]` section. This is
where you can explicitly tell `dgit` two things: if (and where, if necessary)
you have `git-hg` installed, and if (and where, if necessary) you have `hub`
installed:

    [dgit]
    githg = /path/where/githg/lives
    hub = /path/to/hub

If `git-hg` and/or `hub` are already in your `$PATH`, you can omit those lines
from the config entirely, as `dgit` will notice and just Do The Right Thing.

If you have `hub` in your `$PATH` and DON'T want `dgit` to use it, you can just
say:

    [dgit]
    hub = off

in your gitconfig, and `dgit` will jump straight to using `git` instead of also
wrapping it in `hub`.

The second config section is where you set default arguments for normal `git`
commands, a section appropriately called `[defaults]`. Under this section, you
can have an entry for any `git` command where you list the default arguments you
want passed to it all the time. For example, if you always wanted `--stat` as
an argument to `git log`, you would have a `[defaults]` section that looks like:

    [defaults]
    log = --stat

And so on, and so on. This is modeled after mercurial's (now deprecated)
defaults section, so you can google around for info on that if you really need
more help.

BUT WAIT, THERE'S MORE!
=======================

That's right folks, for a limited time only (or not), `dgit` will also let you
use the shortest unique prefix to run a `git` command! Instead of doing, for
example, `git status`, you can just do `git st`! This will also work with your
`git` aliases, so if you have an alias for some really long comand, such as

    [alias]
    fixup = !sh -c 'git commit -m \"fixup! $(git log -1 --format='\\''%s'\\'' $@)\"' -

you could do `git fi` and it would end up running that alias.

WHAT IF I WANT TO RUN A COMMAND WITHOUT DEFAULT ARGS?
=====================================================

Simple, just do `git --nodefaults <other args>`
