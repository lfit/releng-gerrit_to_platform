###############
Troubleshooting
###############

Most common issues
==================

#. Gerrit comment triggers not working

   - Make sure your GH organization accepts Personal Access Tokens
   - Click on Organization Settings, Personal Access Tokens, Settings where setup
     prompt questions will appear to complete the Fine-Grained and Personal token
     configuration.
   - Confirm the token is active under Organization Settings, Personal Access Tokens,
     Active tokens.
   - Make sure the resource owner of the token created by the admin user is set to the
     organizarion and not the user.
