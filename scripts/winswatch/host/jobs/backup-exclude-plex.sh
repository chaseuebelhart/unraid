#!/bin/bash
# ONE-OFF: exclude Plex's regenerable dirs (Media = preview thumbnails/BIF, Cache) from the weekly Appdata.Backup.
# The library database, watch history and settings live elsewhere in appdata and stay backed up.
set -euo pipefail
CFG=/boot/config/plugins/appdata.backup/config.json
cp -a "$CFG" "$CFG.bak-$(date +%Y%m%d-%H%M%S)"
php -r '
$p = "/boot/config/plugins/appdata.backup/config.json";
$c = json_decode(file_get_contents($p), true);
$ex = "Library/Application Support/Plex Media Server/Media\nLibrary/Application Support/Plex Media Server/Cache";
$c["containerSettings"]["Plex-Media-Server"]["exclude"] = $ex;
file_put_contents($p, json_encode($c, JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES));
echo "exclude now: " . str_replace("\n", " | ", $c["containerSettings"]["Plex-Media-Server"]["exclude"]) . "\n";
'
echo "--- verify ---"
php -r '$c=json_decode(file_get_contents("/boot/config/plugins/appdata.backup/config.json"),true);
var_export($c["containerSettings"]["Plex-Media-Server"]); echo "\n";
echo "frequency: ".$c["backupFrequency"]." weekday ".$c["backupFrequencyWeekday"]." at ".$c["backupFrequencyHour"].":".$c["backupFrequencyMinute"]."\n";'
