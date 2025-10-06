============
Contributing
============

Welcome to ``gerrit_to_platform`` contributor's guide.

This document focuses on getting any potential contributor familiarized
with the development processes, but `other kinds of contributions`_ are also
appreciated.

If you are new to using git_ or have never collaborated in a project, please
have a look at `contribution-guide.org`_. Other resources are also listed in
the `guide created by FreeCodeCamp`_ [#contrib1]_.

If you are new to working with Gerrit_, please see our `Gerrit Guide`_

Please notice, we expect all users and contributors to be **open,
considerate, reasonable, and respectful**. When in doubt, `Python Software
Foundation's Code of Conduct`_ is a good reference on terms of behavior
guidelines.


Issue Reports
=============

If you experience bugs or general issues with ``gerrit_to_platform``, please
have a look on the `issue tracker`_. If you don't see anything useful there,
please feel free to fire an issue report.

.. tip::
   Please don't forget to include the closed issues in your search.
   Sometimes a solution was already reported, and the problem now considered
   **solved**.

New issue reports should include information about your programming environment
(e.g., operating system, Python version) and steps to reproduce the problem.
Please try also to simplify the reproduction steps to a minimal example that
still illustrates the problem you are facing. By removing other factors, you
help us to identify the root cause of the issue.


Documentation Improvements
==========================

You can help improve ``gerrit_to_platform`` docs by making them more readable
and coherent, or by adding missing information and correcting mistakes.

``gerrit_to_platform`` documentation uses Sphinx_ as its main documentation
compiler.  This means that the docs are in the same repository as the project
code, and that any documentation update has code review in the same way as a
code contribution.

When working on documentation changes in your local machine, you can
compile them using |tox|_::

    tox -e docs

and use Python's built-in web server for a preview in your web browser
(``http://localhost:8000``)::

    python3 -m http.server --directory 'docs/_build/html'


Code Contributions
==================

`Test-Drive Development`_ is the driving method of development of this code
base. All contributions must come with supporting test cases.

Submit an issue
---------------

Before you work on any non-trivial code contribution it's best to first create
a report in the `issue tracker`_ to start a discussion on the subject.  This
often provides considerations and avoids unnecessary work.

Create an environment
---------------------

Before you start coding, we recommend creating an isolated `virtual
environment`_ to avoid any problems with your installed Python packages.
Do this via either |virtualenv|_::

    virtualenv <PATH TO VENV>
    source <PATH TO VENV>/bin/activate

or Miniconda_::

    conda create -n gerrit_to_platform python=3 six virtualenv pytest pytest-cov
    conda activate gerrit_to_platform

Clone the repository
--------------------

#. Create an user account on |the repository service| if you do not already have one.
#. Clone this copy to your local disk::

    git clone ssh://YourLogin@gerrit.linuxfoundation.org:29418/releng/gerrit_to_platform.git
    cd gerrit_to_platform
    git review -s

#. You should run::

    pip install -U pip setuptools -e .

   to be able to import the package under development in the Python REPL.

#. Install |pre-commit|_::

    pip install pre-commit && pre-commit install

   ``gerrit_to_platform`` comes with a lot of hooks configured to automatically help the
   developer to check the code during creation.

Create your changes
----------------------

#. Create a branch to hold your changes::

    git checkout -b my-feature

   and start making changes. Never work on the main branch!

#. Start your work on this branch. Don't forget to add docstrings_ to new
   functions, modules and classes.

#. Add yourself to the list of contributors in ``AUTHORS.rst``.

#. Add a reno note for changes if they are changelog worthy::

    tox -e reno new my_change_identifier

   and edit the returned file

#. When you’re done editing, do::

    git add <MODIFIED FILES>
    git commit

   to record your changes in git_.

   Please make sure to see the validation messages from |pre-commit|_ and fix
   any eventual issues.
   This should automatically use flake8_/black_ to check/fix the code style
   in a way that is compatible with the project.

   .. important:: Don't forget to add unit tests and documentation in case your
      contribution adds a feature and is not a bugfix.

      Moreover, writing a `descriptive commit message`_ is highly recommended.
      In case of doubt, you can check the commit history with::

         git log --graph --decorate --pretty=oneline --abbrev-commit --all

      to look for recurring communication patterns.

#. Please check that your changes don't break any unit tests with::

    tox

   (after having installed |tox|_ with ``pip install tox`` or ``pipx``).

   You can also use |tox|_ to run other pre-configured tasks in the repository.
   Try ``tox -av`` to see a list of the available checks.

Propose your contribution
-------------------------

#. If everything works fine, push your local branch to |the repository service|
   with::

    git review

#. If your change requires updates follow the procedure for `updating an
   existing patch`_


Troubleshooting
---------------

The following tips can are helpful when facing problems to build or test the
package:

#. Make sure to fetch all the tags from the upstream repository_.
   The command ``git describe --abbrev=0 --tags`` should return the version you
   are expecting. If you are trying to run CI scripts in a fork repository,
   make sure to push all the tags.
   You can also try to remove all the egg files or the complete egg folder, i.e.,
   ``.eggs``, as well as the ``*.egg-info`` folders in the ``src`` folder or
   potentially in the root of your project.

#. Sometimes |tox|_ misses out when adding new dependencies to ``pyproject.toml``
   and ``docs/requirements.txt``. If you find any problems with missing
   dependencies when running a command with |tox|_, try to recreate the ``tox``
   environment using the ``-r`` flag. For example, instead of::

    tox -e docs

   Try running::

    tox -r -e docs

#. Make sure to have a reliable |tox|_ installation that uses the correct
   Python version (e.g., 3.7+). When in doubt you can run::

    tox --version
    # OR
    which tox

   If you have trouble and are seeing weird errors upon running |tox|_, you can
   also try to create a dedicated `virtual environment`_ with a |tox|_ binary
   freshly installed. For example::

    virtualenv .venv
    source .venv/bin/activate
    .venv/bin/pip install tox
    .venv/bin/tox -e all

#. `Pytest can drop you`_ in an interactive session in the case an error
   occurs.  To do that you need to pass a ``--pdb`` option (for example by
   running ``tox -- -k <NAME OF THE FALLING TEST> --pdb``).  You can also setup
   breakpoints manually instead of using the ``--pdb`` option.


Maintainer tasks
================

Releases
--------

If you are part of the group of maintainers and have correct user permissions
on PyPI_, the following steps can release a new version for
``gerrit_to_platform``:

#. Make sure all unit tests are successful.
#. Tag the current commit on the main branch with a signed release tag, e.g.,
   ``git tag -sm 'v1.2.3' v1.2.3``.
#. Push the new tag to the origin repository_, e.g., ``git push v1.2.3``
#. Clean up the ``dist`` and ``build`` folders with ``tox -e clean``
   (or ``rm -rf dist build``)
   to avoid confusion with old builds and Sphinx docs.
#. Run ``tox -e build`` and check that the files in ``dist`` have
   the correct version (no ``.dirty`` or git_ hash) according to the git_ tag.
   Also check the sizes of the distributions, if they are too big (e.g., >
   500KB). Verify that there is no unwanted clutter.
#. Run ``tox -e publish -- --repository pypi`` and check that everything
   uploaded to PyPI_.



.. [#contrib1] Even though, these resources focus on open source projects and
   communities, the general ideas behind collaborating with other developers
   to collectively create software are general and are applicable to all sorts
   of environments, including private companies and proprietary code bases.


.. |the repository service| replace:: Gerrit
.. |contribute button| replace:: "Create pull request"

.. _repository: https://gerrit.linuxfoundation.org/infra/admin/repos/releng/gerrit_to_platform,general
.. _issue tracker: https://github.com/lfit/releng-gerrit_to_platform/issues


.. |virtualenv| replace:: ``virtualenv``
.. |pre-commit| replace:: ``pre-commit``
.. |tox| replace:: ``tox``


.. _black: https://pypi.org/project/black/
.. _CommonMark: https://commonmark.org/
.. _contribution-guide.org: https://www.contribution-guide.org/
.. _descriptive commit message: https://chris.beams.io/posts/git-commit
.. _docstrings: https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html
.. _first-contributions tutorial: https://github.com/firstcontributions/first-contributions
.. _flake8: https://flake8.pycqa.org/en/stable/
.. _Gerrit: https://www.gerritcodereview.com/
.. _Gerrit Guide: https://docs.releng.linuxfoundation.org/en/latest/gerrit.html
.. _git: https://git-scm.com
.. _guide created by FreeCodeCamp: https://github.com/FreeCodeCamp/how-to-contribute-to-open-source
.. _Miniconda: https://docs.conda.io/en/latest/miniconda.html
.. _other kinds of contributions: https://opensource.guide/how-to-contribute
.. _pre-commit: https://pre-commit.com/
.. _PyPI: https://pypi.org/
.. _Pytest can drop you: https://docs.pytest.org/en/stable/how-to/failures.html#using-python-library-pdb-with-pytest
.. _Python Software Foundation's Code of Conduct: https://www.python.org/psf/conduct/
.. _Sphinx: https://www.sphinx-doc.org/en/master/
.. _Test-Drive Development: https://en.wikipedia.org/wiki/Test-driven_development
.. _tox: https://tox.wiki/en/stable/
.. _updating an existing patch: https://docs.releng.linuxfoundation.org/en/latest/gerrit.html#update-an-existing-patch
.. _virtual environment: https://realpython.com/python-virtual-environments-a-primer/
.. _virtualenv: https://virtualenv.pypa.io/en/stable/
