.. These are examples of badges you might want to add to your README:
   please update the URLs accordingly

    .. image:: https://readthedocs.org/projects/gerrit_to_platform/badge/?version=latest
        :alt: ReadTheDocs
        :target: https://gerrit_to_platform.readthedocs.io/en/stable/
    .. image:: https://img.shields.io/pypi/v/gerrit_to_platform.svg
        :alt: PyPI-Server
        :target: https://pypi.org/project/gerrit_to_platform/
    .. image:: https://img.shields.io/conda/vn/conda-forge/gerrit_to_platform.svg
        :alt: Conda-Forge
        :target: https://anaconda.org/conda-forge/gerrit_to_platform
    .. image:: https://pepy.tech/badge/gerrit_to_platform/month
        :alt: Monthly Downloads
        :target: https://pepy.tech/project/gerrit_to_platform
    .. image:: https://img.shields.io/twitter/url/http/shields.io.svg?style=social&label=Twitter
        :alt: Twitter
        :target: https://twitter.com/gerrit_to_platform

.. image:: https://github.com/lfit/releng-gerrit_to_platform/actions/workflows/gerrit-verify.yaml/badge.svg
    :alt: Build Status
    :target: https://github.com/lfit/releng-gerrit_to_platform/actions/workflows/gerrit-verify.yaml

.. image:: https://img.shields.io/coveralls/github/lfit/releng-gerrit_to_platform/main.svg
    :alt: Coveralls
    :target: https://coveralls.io/r/lfit/releng-gerrit_to_platform

.. image:: https://img.shields.io/badge/-PyScaffold-005CA0?logo=pyscaffold
    :alt: Project generated with PyScaffold
    :target: https://pyscaffold.org/

|

==================
gerrit_to_platform
==================


    Gerrit_ to GitHub_ / GitLab_ (not yet available)


Gerrit hooks to allow using GitHub and GitLab as CI platforms.

To use, install the Gerrit hooks_ plugin and then symlink the hooks from the
virtualenv that has the package installed.

A Python 3.8 or greater environment

Repositories that use the CI platform must have full mirroring replication
configured. In specific ``refs/*`` must be in the replication set and not
``refs/heads/*``

To activate a given hook, symlink the installed hook in the gerrit hooks
directory.

Two configuration files needed. These files are:

- ``~gerrituser/.config/gerrit_to_platform/gerrit_to_platform.ini``
- ``~gerrituser/.config/gerrit_to_platform/replication.config``

The replication.config file should be a symlink to the standard Gerrit
replication.config file

The ``gerrit_to_platform.ini`` file has the following format::

    [mapping "content-added"]
    recheck = verify
    remerge = merge

    [github.com]
    token = <a_token_that_allows_triggering_actions>

    [gitlab.com]
    token = <a_token_that_allows_triggring_workflows>


The ``content-added`` mapping section is a key value pair for comment triggers
to the corresponding workflow name or filename

.. _Gerrit: https://www.gerritcodereview.com/
.. _GitHub: https://github.com
.. _GitLab: https://gitlab.com
.. _hooks: https://gerrit.googlesource.com/plugins/hooks/+doc/master/src/main/resources/Documentation/about.md

.. _pyscaffold-notes:

Making Changes & Contributing
=============================

This project uses `pre-commit`_, please make sure to install it before making any
changes::

    pip install pre-commit
    cd gerrit_to_platform
    pre-commit install
    pre-commit install -t commit-msg

Don't forget to tell your contributors to also install and use pre-commit.

.. _pre-commit: https://pre-commit.com/

Note
====

PyScaffold 4.4 provided the initial project setup. For details and usage
information on PyScaffold see https://pyscaffold.org/.
