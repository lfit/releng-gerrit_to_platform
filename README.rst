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
gerrit-to-platform
==================


    Gerrit_ to GitHub_ / GitLab_ (not yet available)


Gerrit hooks to allow using GitHub and GitLab as CI platforms.

To use, install the Gerrit hooks_ plugin and then symlink the hooks from the
virtualenv that has the package installed.

You need to have a Python 3.11 or greater environment.

Repositories that use the CI platform must have full mirroring replication
configured. In specific ``refs/*`` must be in the replication set and not
``refs/heads/*``

To activate a given hook, symlink the installed hook in the gerrit hooks
directory.

You need two configuration files:

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
    token = <a_token_that_allows_triggering_workflows>


The ``content-added`` mapping section is a key value pair for comment triggers
to the corresponding workflow name or filename

GitHub Workflow Configuration
=============================

There are three hooks that gerrit-to-platform handles:

* patchset-created (search filter: verify)
* change-merged (search filter: merge)
* comment-added (comment mapping for keyword to search filter)

Configuration for triggered workflows must meet the following requirements:

* The workflow filename must contain 'gerrit'
* The workflow filename must contain the search filter

Required workflows (those that should run on all projects) must be part of the
ORGANIZATION/.github magic repository.
These workflow filenames must also contain 'required'.

ex: ``.github/workflows/gerrit-required-verify.yaml``

You can put standard workflows (non-required ones) into a project's repository,
in the .github directory. These should have filenames that include 'gerrit' and
the search filter, as discussed above, but do not need anything beyond. They
should never include 'required' in their filename.

ex: ``.github/workflows/gerrit-merge.yaml`` or
``.github/workflows/gerrit-sonar-novote-verify.yaml``

All workflows must have the following primary configuration::

    ---
    name: Gerrit Verify

    # yamllint disable-line rule:truthy
    on:
      workflow_dispatch:
        inputs:
          GERRIT_BRANCH:
            description: 'Branch that change is against'
            required: true
            type: string
          GERRIT_CHANGE_ID:
            description: 'The ID for the change'
            required: true
            type: string
          GERRIT_CHANGE_NUMBER:
            description: 'The Gerrit number'
            required: true
            type: string
          GERRIT_CHANGE_URL:
            description: 'URL to the change'
            required: true
            type: string
          GERRIT_EVENT_TYPE:
            description: 'Gerrit event type'
            required: true
            type: string
          GERRIT_PATCHSET_NUMBER:
            description: 'The patch number for the change'
            required: true
            type: string
          GERRIT_PATCHSET_REVISION:
            description: 'The revision sha'
            required: true
            type: string
          GERRIT_PROJECT:
            description: 'Project in Gerrit'
            required: true
            type: string
          GERRIT_REFSPEC:
            description: 'Gerrit refspec of change'
            required: true
            type: string


    concurrency:
      group: ${{ github.event.inputs.GERRIT_CHANGE_ID || github.run_id }}
      cancel-in-progress: true

    jobs:
      <your_job_configurations>

Required workflows must have the following extra input::

    TARGET_REPO:
      description: 'The target GitHub repository needing the required workflow'
      required: true
      type: string


Making Changes & Contributing
=============================

This project uses `pre-commit`_, please make sure to install it before making any
changes::

    pip install pre-commit
    cd gerrit_to_platform
    pre-commit install
    pre-commit install -t commit-msg

Don't forget to tell your contributors to also install and use pre-commit.

Note
====

PyScaffold 4.4 provided the initial project setup. For details and usage
information on PyScaffold see https://pyscaffold.org/.

.. _Gerrit: https://www.gerritcodereview.com/
.. _GitHub: https://github.com
.. _GitLab: https://gitlab.com
.. _hooks: https://gerrit.googlesource.com/plugins/hooks/+doc/master/src/main/resources/Documentation/about.md
.. _pre-commit: https://pre-commit.com/
