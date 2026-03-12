   Gerrit-to-GitHub Trigger Mechanism Summary

   For workflows in regular project repos (non-.github repos):

   The workflows must be placed in the .github/workflows/ directory of the
   repository that is mirrored from Gerrit to GitHub. They do NOT need the
   TARGET_REPO parameter.

   KEY REQUIREMENTS:

     - Workflow filename conventions:
       - Must contain gerrit in the filename
       - Must contain the search filter (verify or merge)
       - Example: gerrit-packer-verify.yaml, gerrit-packer-merge.yaml
     - Workflow dispatch inputs:
       - All standard Gerrit inputs (GERRIT_BRANCH, GERRIT_CHANGE_ID, etc.) - exactly as shown in the reference workflow
     - Repository mirroring:
       - Full refs/* replication from Gerrit (not just refs/heads/*)
       - This ensures all patchset refs are available on GitHub
     - Workflow triggers:
       - patchset-created → triggers workflows with verify in filename
       - change-merged → triggers workflows with merge in filename
       - comment-added → can trigger based on keyword mapping in config

   TARGET_REPO is ONLY needed for:

     - Required workflows in the ORG/.github repository
     - These are organization-wide workflows that run on all projects
     - Regular project-specific workflows do NOT use TARGET_REPO

   Conclusion: Your examples/workflows do NOT need TARGET_REPO. They should work as
   standard project-specific Gerrit-triggered workflows.

