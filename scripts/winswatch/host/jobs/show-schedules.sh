#!/bin/bash
# READ-ONLY: dump every scheduled thing on the host so a new job can be slotted without a collision.
set -uo pipefail
echo "=== user.scripts schedule.json ==="; cat /boot/config/plugins/user.scripts/schedule.json 2>/dev/null
echo; echo "=== customSchedule.cron ==="; cat /boot/config/plugins/user.scripts/customSchedule.cron 2>/dev/null
echo; echo "=== /etc/cron.d/root ==="; cat /etc/cron.d/root 2>/dev/null
echo; echo "=== backup_appdata script (head) ==="; head -40 /boot/config/plugins/user.scripts/scripts/backup_appdata/script 2>/dev/null
echo; echo "=== CA appdata backup plugin cfg ==="; cat /boot/config/plugins/ca.backup2/ca.backup2.cfg 2>/dev/null || echo "(no ca.backup2 cfg)"
cat /boot/config/plugins/appdata.backup/appdata.backup.cfg 2>/dev/null || echo "(no appdata.backup cfg)"
echo; echo "=== parity check schedule ==="; grep -i -E "parity|cron" /boot/config/plugins/dynamix/dynamix.cfg 2>/dev/null | head -20
