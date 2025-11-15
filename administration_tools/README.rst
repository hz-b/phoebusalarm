Administration scripts
======================

How to push commits from the upstream- to the downstream repository
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

This procedure would usually only require a "push" command on the command line.
However, when the upstream- and downstream repository use different version
control systems, things are more complicated.

The helper script ``downstream-make-repo.sh`` uses a repository conversion script,
"repo-mirror.sh" from the `bii_scripts <https://bii-scripts.sourceforge.io/>`_
project.

Run::

  ./downstream-make-repo.sh

When your repository is placed at ``filepath/myrepo``, the helper script
creates extra repositories at ``filepath``.

The repository ``filepath/myrepo-downstream`` is the one that is used to push
changes to the downstream repository at the repository hoster. To push these
changes run::

  bash ./downstream-push.sh

Note: Do NOT record ANY changes in the created downstream repository.

Interactive shell
+++++++++++++++++

This may be useful to fix problems on the downstream hosting site::

  ./downstream-shell.sh

Pull from upstream
++++++++++++++++++

In your upstream working copy you can pull upstream changes with::

  ./upstream-pull.sh

Push to upstream
++++++++++++++++

In your upstream working copy you can push changes to upstream with::

  bash ./upstream-push.sh

Configuration data
++++++++++++++++++

All script configuration is in file config.dat. You usually don't change
this file but you can look up repository URLs and other things in this file.

