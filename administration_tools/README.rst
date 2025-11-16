Administration scripts
======================

How to push commits from the upstream- to the downstream repository
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

To push these changes run::

  bash ./downstream-push.sh

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

