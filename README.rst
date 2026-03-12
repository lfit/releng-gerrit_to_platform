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

    [parrotbot]
    enabled = true


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


ChatOps Workflow
================

Trigger GitHub Actions workflows directly from Gerrit by adding comments to your
changes. This eliminates the need for manual workflow triggers and enables
automated testing on-demand.

To trigger a workflow, add a comment to any Gerrit change using the pattern::

    gha-<action> <workflow-name> <parameters>

For example::

    gha-run csit-2n-perftest nic=intel-e810cq drv=avf

Common examples include::

    gha-run csit-2n-perftest nic=intel-e810cq drv=avf
    gha-run csit-3n-perftest mrrANDnic_intel-e810cqANDdrv_avfAND4c
    gha-run csit-2n-mrr-weekly
    gha-run csit-3n-mrr-daily nic=intel-x710
    gha-run terraform-cdash-deploy env=production
    gha-run terraform-infra-update region=us-west
    gha-run vpp-build type=release arch=x86_64
    gha-run vpp-verify compiler=gcc
    gha-run hicn-verify arch=amd64
    gha-run cicn-build type=debug
    gha-run hc2vpp-integration-test
    gha-run hc2vpp-verify

Specify parameters in two formats:

1. Key=Value format (recommended)::

    gha-run csit-2n-perftest nic=intel-e810cq drv=avf framesize=64

2. AND-separated format (legacy support)::

    gha-run csit-2n-perftest mrrANDnic_intel-e810cqANDdrv_avfAND4c

**Cooldown Period**: To prevent workflow spam, there is a 5-minute cooldown
between commands for the same workflow on the same change. If you trigger a
workflow and need to run it again, wait 5 minutes before commenting.

**Troubleshooting**: If your command doesn't trigger a workflow:

* Verify the command starts with ``gha-`` followed by the action and workflow name
* Check that the workflow name matches a supported pattern for your project
* Wait 5 minutes if you triggered the same workflow on this change within the last 5 minutes
* Review GitHub Actions logs for error messages

**Workflow Configuration**: Name workflows that respond to ChatOps commands
``comment-handler`` and include a ``GERRIT_COMMENT`` input that receives
the full command line. The workflow then parses the command to determine which
handler to execute. See ``gerrit-comment-handler.yaml`` for a complete example.


Workflow Migration Guide
========================

This section helps teams migrate from vanilla GitHub workflows (or Jenkins jobs)
to Gerrit-integrated GitHub Actions workflows. The ``examples/workflows/``
directory contains annotated example workflows.

Example Workflows
-----------------

Four example workflows progress from a standard GitHub workflow to increasingly
Gerrit-integrated patterns:

1. ``examples/workflows/github-vanilla-verify.yaml`` — A pure GitHub workflow
   with no Gerrit dependencies. Serves as the baseline showing standard
   ``pull_request``, ``push``, and ``workflow_dispatch`` triggers with
   ``actions/checkout``.

2. ``examples/workflows/gerrit-verify.yaml`` — The Gerrit-integrated verify
   counterpart. Demonstrates the clear-vote → build → vote pattern with
   ``checkout-gerrit-change-action`` and all nine ``GERRIT_*`` inputs.

3. ``examples/workflows/gerrit-merge.yaml`` — The Gerrit-integrated post-merge
   workflow. Shows comment-only mode (no voting on merged changes), standard
   ``actions/checkout``, and the replication delay pattern.

4. ``examples/workflows/gerrit-verify-manual-dispatch.yaml`` — A verify
   workflow that supports both Gerrit dispatch and manual runs from the
   GitHub Actions UI. Demonstrates optional inputs, conditional Gerrit jobs,
   and adaptive checkout strategy.

Verify vs. Merge Patterns
--------------------------

Gerrit workflows fall into two fundamental patterns based on the hook that
triggers them:

**Verify workflows** (``patchset-created`` hook, search filter: ``verify``):

* Test *unmerged* changes (open Gerrit patchsets)
* **Must vote** on the change: ``Verified +1`` (success) or ``Verified -1``
  (failure)
* Clear any previous vote at the start of the run
* **Must use** ``checkout-gerrit-change-action`` — the standard
  ``actions/checkout`` cannot see unmerged Gerrit change refs
  (e.g., ``refs/changes/40/11540/1``) on the GitHub mirror
* Job structure: ``clear-vote`` → ``build-and-test`` → ``vote``

**Merge workflows** (``change-merged`` hook, search filter: ``merge``):

* Run *after* a change lands on the target branch
* **Cannot vote** on a merged/closed change — use ``comment-only: "true"``
  to post status comments instead
* **Use standard** ``actions/checkout`` — the merged code is already on the
  branch HEAD in the GitHub mirror
* Add a replication delay (``sleep 10s``) before checkout to allow the
  Gerrit replication plugin to sync the merged commit to GitHub
* Job structure: ``notify`` (comment-only) → ``build-and-publish`` →
  ``report-status`` (comment-only)

Checkout Rules
--------------

Choosing the correct checkout action is the single most important difference
between verify and merge workflows:

.. list-table::
   :header-rows: 1
   :widths: 20 35 45

   * - Workflow Type
     - Checkout Action
     - Why
   * - **Verify**
     - ``lfreleng-actions/checkout-gerrit-change-action``
     - Fetches the unmerged change ref from the Gerrit server (or GitHub mirror
       if replicated). ``actions/checkout`` will not find these refs.
   * - **Merge**
     - ``actions/checkout`` with ``ref: ${{ inputs.GERRIT_BRANCH }}``
     - The change already exists in the branch. No special ref fetching
       required. Add a replication delay before checkout.
   * - **Manual dispatch**
     - ``actions/checkout`` (no ref override needed)
     - Checks out the branch selected in the GitHub UI (``github.ref``).

Voting Rules
------------

.. list-table::
   :header-rows: 1
   :widths: 15 25 60

   * - Workflow Type
     - Voting
     - Details
   * - **Verify**
     - Full voting
     - ``clear`` at start, ``success``/``failure``/``cancelled`` at end.
       Uses ``gerrit-review-action`` with ``vote-type``.
   * - **Merge**
     - Comment-only
     - Set ``comment-only: "true"`` on all ``gerrit-review-action`` steps.
       Attempting to vote on a merged change will fail.
   * - **Advisory verify**
     - Comment-only
     - Non-blocking verify checks can use ``comment-only: "true"`` to post
       results without affecting the Verified label. Add a ``comment-only``
       input to toggle this behavior (see production workflow
       ``gerrit-required-info-yaml-verify.yaml`` for an example).

Concurrency Groups
------------------

Gerrit workflows should key their concurrency group on ``GERRIT_CHANGE_ID``::

    concurrency:
      group: ${{ github.event.inputs.GERRIT_CHANGE_ID || github.run_id }}
      cancel-in-progress: true

This ensures that pushing a new patchset to the same Gerrit change cancels any
in-progress run for the previous patchset. The ``github.run_id`` fallback
prevents issues when inputs are absent (e.g., manual dispatch).

Replication Delay
-----------------

Gerrit-to-GitHub replication is asynchronous. Workflows should include a brief
sleep (typically 10 seconds) to allow refs to propagate to the GitHub mirror:

* **Verify workflows**: The ``clear-vote`` job includes ``sleep 10s`` after
  clearing the vote. Because the build job waits for ``clear-vote`` via
  ``needs:``, the delay fits in naturally.
* **Merge workflows**: The ``notify`` job includes ``sleep 10s`` after posting
  the start comment. This gives the merged commit time to appear on the mirror
  before the build job runs ``actions/checkout``.

The ``checkout-gerrit-change-action`` also accepts a ``delay`` parameter for
extra delay, though setting ``delay: "0s"`` is common when a preceding job
already includes the replication sleep.

Manual Dispatch Bypass Pattern
------------------------------

For workflows where running from the GitHub Actions UI is valuable (debugging,
on-demand checks, advisory scans), the manual dispatch bypass pattern adds:

1. A ``MANUAL_DISPATCH`` boolean input (default: ``false``)
2. All ``GERRIT_*`` inputs marked ``required: false`` with empty defaults
3. Conditional ``if:`` guards on Gerrit-specific jobs (``clear-vote``, ``vote``)
4. Dual checkout steps — one for Gerrit dispatch, one for manual dispatch —
   with ``if:`` conditions keyed on ``GERRIT_REFSPEC``

When ``gerrit_to_platform`` dispatches the workflow, it populates all inputs
and ``MANUAL_DISPATCH`` defaults to ``false``, so the workflow behaves
identically to a standard Gerrit verify. When a developer clicks "Run workflow"
in the GitHub UI, the workflow skips Gerrit jobs and uses standard checkout.

See ``examples/workflows/gerrit-verify-manual-dispatch.yaml`` for the complete
annotated example.

.. note::

   This pattern is best suited for advisory/non-blocking workflows.
   Required gating workflows should always use the standard verify pattern
   with ``required: true`` inputs to ensure nothing bypasses the Gerrit
   integration.

Required (Organization-Wide) Workflows
---------------------------------------

Workflows that must run on *every* repository in the organization live in
the ``ORGANIZATION/.github`` magic repository. These have extra requirements:

* The filename must include ``required`` (e.g., ``gerrit-required-verify.yaml``)
* An extra ``TARGET_REPO`` input tells the workflow which repository to
  check out::

      TARGET_REPO:
        description: 'The target GitHub repository needing the required workflow'
        required: true
        type: string

* Set the ``checkout-gerrit-change-action`` ``repository`` parameter
  to ``${{ inputs.TARGET_REPO }}``

``workflow_dispatch`` Input Limit
---------------------------------

GitHub enforced a hard limit of **10 inputs** for ``workflow_dispatch`` events
until December 2025. With 9 standard ``GERRIT_*`` inputs, this left
**1 slot** for custom workflow parameters — a severe constraint for teams
that required extra inputs.

**In December 2025, GitHub raised this limit from 10 to 25 inputs.** This
change relieves the constraint, leaving 16 slots for custom parameters
alongside the 9 ``GERRIT_*`` inputs. See the `GitHub changelog
announcement
<https://github.blog/changelog/2025-12-04-actions-workflow-dispatch-workflows-now-support-25-inputs/>`_
for details.

For detailed background on this constraint and alternative workarounds (such as
using ``repository_dispatch`` with unlimited ``client_payload`` fields), see
``docs/GITHUB_WORKFLOW_INPUT_LIMIT_SOLUTION.md``.

Companion GitHub Actions
-------------------------

Two GitHub Actions are essential for Gerrit-integrated workflows:

**gerrit-review-action** (``lfreleng-actions/gerrit-review-action``):
  Posts votes (``Verified +1/-1``) and comments on Gerrit changes via SSH.
  Supports vote types: ``clear``, ``success``, ``failure``, ``cancelled``.
  Set ``comment-only: "true"`` for merge workflows and advisory checks.

**checkout-gerrit-change-action** (``lfreleng-actions/checkout-gerrit-change-action``):
  Fetches unmerged Gerrit change refs (e.g., ``refs/changes/YY/NNYY/Z``) from
  the GitHub mirror or falls back to the Gerrit server directly. Required for
  all verify workflows because ``actions/checkout`` cannot see unmerged refs.

.. note::

   The example workflows reference these actions with ``@main`` for
   readability. **Production workflows should pin to a specific commit SHA**
   (e.g., ``@537251ec667665b386f70b330b05446e3fc29087``) for reproducibility
   and security. See the workflows in ``releng-reusable-workflows`` for
   real-world pinned examples.

Quick Reference: Vanilla → Gerrit Migration Checklist
------------------------------------------------------

When converting a standard GitHub workflow to a Gerrit-integrated one:

.. list-table::
   :header-rows: 1
   :widths: 5 45 50

   * - #
     - Task
     - Notes
   * - 1
     - Replace triggers with ``workflow_dispatch`` + 9 ``GERRIT_*`` inputs
     - Remove ``pull_request``, ``push`` triggers entirely
   * - 2
     - Set concurrency group to ``GERRIT_CHANGE_ID``
     - Replaces ``github.head_ref`` or branch-based grouping
   * - 3
     - Add ``clear-vote`` job at the start (verify)
     - Resets previous ``Verified`` votes; includes replication sleep
   * - 4
     - Replace ``actions/checkout`` (verify)
     - Use ``checkout-gerrit-change-action`` with ``gerrit-refspec``,
       ``gerrit-project``, ``gerrit-url``, and ``ref``
   * - 5
     - Add ``vote`` job at the end (verify)
     - Must use ``if: ${{ always() }}`` to report even on failure
   * - 6
     - For merge workflows, use ``comment-only: "true"``
     - Keep ``actions/checkout`` but add replication sleep before it
   * - 7
     - Name the file appropriately
     - Must contain ``gerrit`` and the search filter (``verify`` or ``merge``)
   * - 8
     - Configure repository variables and secrets
     - ``GERRIT_SERVER``, ``GERRIT_SSH_USER``, ``GERRIT_SSH_PRIVKEY``,
       ``GERRIT_KNOWN_HOSTS``, ``GERRIT_URL``


Parrotbot — Dependabot Command Relay
=====================================

Parrotbot allows Gerrit committers to issue commands to GitHub bots (such as
Dependabot) directly from Gerrit comments. This is necessary because GitHub
mirrors of Gerrit repositories function as non-writable replicas, and project committers
lack the GitHub admin/push permissions to interact with bots like
Dependabot.

When a committer posts a parrotbot command on a Gerrit change, the bot verifies
the user is a member of the project's committer (owner) group and then posts the
corresponding ``@dependabot`` (or other bot) comment on the linked GitHub
pull request.

**Enabling Parrotbot**

Add the following to ``gerrit_to_platform.ini``::

    [parrotbot]
    enabled = true

Parrotbot reuses the ``[github.com] token`` already configured for workflow
dispatch. The token must have permission to post comments on pull requests in
the target GitHub organisation.

**Usage**

Add a comment to any Gerrit change using one of these patterns::

    @parrot @dependabot <command>
    @parrotbot @dependabot <command>

Supported commands:

* ``recreate`` — Close and recreate the PR from scratch
* ``rebase`` — Rebase the PR onto the latest base branch
* ``merge`` — Merge the PR (if auto-merge conditions pass)
* ``squash`` — Squash and merge the PR
* ``close`` — Close the PR without merging
* ``reopen`` — Reopen a closed PR

**Examples**::

    @parrot @dependabot recreate
    @parrotbot @dependabot rebase

**How It Works**

1. The ``comment-added`` hook checks incoming comments for parrotbot commands
2. The commenter's membership in the project's committer group undergoes
   verification via the Gerrit REST API
3. The linked GitHub pull request gets matched from the Gerrit change's
   topic or commit message to an open PR
4. The bot posts the command as a comment (e.g. ``@dependabot recreate``) on the
   GitHub PR using the configured token
5. A confirmation or error reply gets posted back to the Gerrit change

**Troubleshooting**

* Ensure ``[parrotbot] enabled = true`` appears in the configuration
* The commenter must be a member of the project's committer (owner) group
* The GitHub token must have ``issues:write`` or ``pull_requests:write`` scope
* The Gerrit change must link to a GitHub PR (via topic or change metadata)
* The bot accepts the commands listed above; it ignores unrecognised commands


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
