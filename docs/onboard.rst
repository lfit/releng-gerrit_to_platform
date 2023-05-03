#######
Onboard
#######

gerrit-to-platform requires prior configuration in ``GitHub``

.. _github-config:

GitHub configuration
====================

A `Personal Access Token` is needed to open communication between Gerrit and GitHub.
Prior to that, token policies need to be reviewed and updated if needed.

**GitHub documentation**

- `Token Policies <https://docs.github.com/en/organizations/managing-programmatic-access-to-your-organization/setting-a-personal-access-token-policy-for-your-organization>`_
- `Creating a Token <https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token>`_

Steps to make sure your Token Policies are updated

#. Login into your project's GitHub account using the project's owner credentials
#. Click on your project's organization (If multiple are found under the owner's account)
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
#. Set an expiration date of 1 year (Might want to keep track of this date via calendar reminder)
#. Optionally add a description
#. Make sure the resource owner is set to your `Project's Organization` and not your User
#. Select `All Repositories` option
#. Repository permissions should be `Actions: read and write` and `Contents and Metadata: read`
#. Copy your token and be ready to update it in puppet

   .. note::

      If the token was created using a project's owner account, it is approved
      automatically.

      To make sure, navigate to your Org->Settings->Personal access tokens->Active tokens
      and notice your token listed.
