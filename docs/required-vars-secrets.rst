#########################
Required Vars and Secrets
#########################

This is the inital list of Variables and Secrets needed to be set for your organization

.. _secrets-variables-config:

GitHub Secrets and variables configuration
==========================================

**GitHub documentation**

- `Secrets and Vars <https://docs.github.com/en/actions/security-guides/encrypted-secrets>`_

Steps to set your secrets and variables

#. Login into your project's GitHub account using the project's owner credentials
#. Click on your project's organization (If multiple are found under the owner's account)
#. Click on `Settings` (last tab in the menu)
#. Expand the `Secrets and variables` menu from the panel in the left
#. Click on `Actions`

Required Secrets

- GERRIT_SSH_PRIVKEY - The private SSH key used to talk to gerrit (You can use lftools to obtain it)
- MAIL_PASSWORD - The AWS mail password used if you are going to need to do mail
- MAIL_USER - The AWS mail password used if you are going to need to do mail

Required Variables

- GERRIT_KNOWN_HOSTS - The known_hosts file contents ``ssh-keyscan -p 29418 <gerrit_server> 2>/dev/null``
- GERRIT_SERVER - For example ``gerrit.onap.org``
- GERRIT_SSH_USER - The username of the account that is used during SSH connections to Gerrit
- MAIL_SERVER - Needed if you are going to need to do mail
- MAIL_SERVER_PORT - Needed if you are going to need to do mail
