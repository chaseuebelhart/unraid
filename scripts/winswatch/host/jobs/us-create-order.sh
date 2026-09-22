#!/bin/bash
# ONE-OFF (Task 7): create the User Scripts entry "winswatch-order" (Custom schedule 45 5 * * *, server clock) exactly the
# way the plugin's exec.php does it (scripts/<name>/{name,script}, schedule.json + /tmp copy, customSchedule.cron, update_cron).
# Used because the Unraid UI session had expired; re-runnable (idempotent).
set -euo pipefail
D=/boot/config/plugins/user.scripts
N=winswatch-order
mkdir -p "$D/scripts/$N"
printf '%s' "$N" > "$D/scripts/$N/name"
printf '#!/bin/bash\nbash /mnt/user/appdata/scripts/winswatch/host/jobs/order.sh\n' > "$D/scripts/$N/script"
php -r '
$D="/boot/config/plugins/user.scripts"; $N="winswatch-order";
$s=json_decode(file_get_contents("$D/schedule.json"),true);
$k="$D/scripts/$N/script";
$s[$k]=["script"=>$k,"frequency"=>"custom","id"=>"schedule".$N,"custom"=>"45 5 * * *"];
$json=json_encode($s,JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES);
file_put_contents("$D/schedule.json",$json); file_put_contents("/tmp/user.scripts/schedule.json",$json);
$cron="";
foreach($s as $e){ if($e["frequency"]=="custom" && $e["custom"]) $cron.=trim($e["custom"])." /usr/local/emhttp/plugins/user.scripts/startCustom.php ".$e["script"]." > /dev/null 2>&1\n"; }
file_put_contents("$D/customSchedule.cron","# Generated cron schedule for user.scripts\n$cron\n");
'
/usr/local/sbin/update_cron
echo "--- scripts/$N:"; ls -la "$D/scripts/$N"; cat "$D/scripts/$N/script"
echo "--- schedule.json entry:"; grep -A4 "\"$D/scripts/$N/script\": {" "$D/schedule.json"
echo "--- customSchedule.cron:"; cat "$D/customSchedule.cron"
echo "--- /etc/cron.d/root (user.scripts lines):"; grep "user.scripts" /etc/cron.d/root
