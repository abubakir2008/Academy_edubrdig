#!/bin/bash
# Forced command for the restricted `academy_deploy_key` in root's
# authorized_keys (see DEPLOY.md) -- SSH puts whatever command the caller
# asked for into $SSH_ORIGINAL_COMMAND, which we validate against an
# allowlist before running anything. This is what stands between "this key
# leaked out of GitHub Actions" and "attacker has an arbitrary root shell":
# the key can only ever reach this script, and this script only ever runs
# one of the two deploy scripts below.
case "$SSH_ORIGINAL_COMMAND" in
  backend)
    exec /usr/local/bin/deploy-academy-backend.sh
    ;;
  frontend)
    exec /usr/local/bin/deploy-academy-frontend.sh
    ;;
  *)
    echo "academy-deploy-dispatch: unknown command '$SSH_ORIGINAL_COMMAND'" >&2
    exit 1
    ;;
esac
