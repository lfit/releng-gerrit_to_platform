#######
Onboard
#######

gerrit-to-platform requires prior configuration in ``GitHub``

.. _github-config:

GitHub configuration
====================

Use a `Personal Access Token` to open communication between Gerrit and GitHub.
Review and update your token policies.

**GitHub documentation**

- `Token Policies <https://docs.github.com/en/organizations/managing-programmatic-access-to-your-organization/setting-a-personal-access-token-policy-for-your-organization>`_
- `Creating a Token <https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token>`_

Steps to update your Token Policies

#. Login into your project's GitHub account using the project's owner credentials
#. Click on your project's organization
#. Click on `Settings` (last tab in the menu)
#. Expand the `Personal access tokens` menu from the panel in the left
#. Click on `Settings`
#. Make sure tokens have allow access and require administration approval

Steps to create the Personal Access Token

#. Once logged in with the project's owner account, click on the user tab in the top right corner
#. Click on `Settings`
#. Find the `Developer Settings` option in the menu on the left
#. Select and expand `Personal Access Tokens`
#. Select `Fine-grained tokens`
#. Click `Generate new token`
#. Use a meaningful name `Gerrit to Platform token for GHA`
#. Set a date of 1 year (Might want to keep track of this date via calendar reminder)
#. Optionally add a description
#. Make sure the resource owner is your `Project's Organization` and not your User
#. Select `All Repositories` option
#. Repository permissions should be `Actions: read and write` and `Contents and Metadata: read`
#. Copy your token and be ready to update it in puppet

   .. note::

      Create your token using a project's owner account for automatic approval.

      To make sure, navigate to your Org->Settings->Personal access tokens->Active tokens
      and notice your token listed.
