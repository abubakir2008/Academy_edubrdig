#!/bin/bash
# Run this on the server (from anywhere) to bootstrap the first admin
# account. Copies create_admin.py into the running identity container and
# executes it there — see that file's docstring for why it has to run
# inside the container.
#
# Usage:
#   create-admin.sh you@example.com "Your Name" [role]
#   role defaults to super_admin; also accepts admin or moderator.
set -euo pipefail

EMAIL="${1:?Usage: $0 <email> <full name> [role]}"
FULL_NAME="${2:?Usage: $0 <email> <full name> [role]}"
ROLE="${3:-super_admin}"
CONTAINER="academy_identity"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

docker cp "$HERE/create_admin.py" "$CONTAINER:/tmp/create_admin.py"
# No -t: this needs to work over a non-interactive SSH exec (no PTY
# available there), and create_admin.py never reads stdin anyway.
docker exec -i "$CONTAINER" python /tmp/create_admin.py \
  --email "$EMAIL" --full-name "$FULL_NAME" --role "$ROLE"
