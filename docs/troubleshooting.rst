###############
Troubleshooting
###############

Most common issues
==================

#. Gerrit triggers not working

   - Make sure your GH organization accepts Personal Access Tokens
   - Click on Organization Settings, Personal Access Tokens, Settings where setup
     prompt questions will appear to complete the Fine-Grained and Personal token
     configuration.
   - Confirm the token is active under Organization Settings, Personal Access Tokens,
     Active tokens.
   - Make sure the resource owner of the token created by the admin user is the
     organization and not the user.

Additional troubleshooting
==========================

#. Manually craft a trigger and see if there is an error

   - Login to the Gerrit system and switch to the Gerrit user
   - Execute a trigger hook as if a new event has just happened:

     .. code-block:: bash

        ./hooks/patchset-created --change <repo_path_in_gerrit>~<branch>~<changsetID_starts_with_I> /
        --kind REWORK --change-url <the_URL_to_the_change> --change-owner "Foo <foo@bar.com>" /
        --change-owner-username foo --project <repo_path_in_gerrit> --branch <branch> --topic <topic_or_''> /
        --uploader "Foo <foo@bar.com>" --uploader-username foo --commit <commit_sha> --patchset <patchset_number>

   - If there are problems, you will see the exact error generated
