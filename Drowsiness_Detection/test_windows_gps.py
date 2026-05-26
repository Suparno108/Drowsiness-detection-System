import subprocess
import re

def get_windows_gps():
    ps_command = (
        'Add-Type -AssemblyName System.Device; '
        '$GeoWatcher = New-Object System.Device.Location.GeoCoordinateWatcher; '
        '$GeoWatcher.Start(); '
        '$timeout = 20; '
        'while (($GeoWatcher.Status -eq "NoData" -or $GeoWatcher.Status -eq "Initializing") -and $timeout -gt 0) { '
        '  Start-Sleep -Milliseconds 200; '
        '  $timeout--; '
        '}; '
        'if ($GeoWatcher.Status -eq "Ready") { '
        '  $loc = $GeoWatcher.Position.Location; '
        '  Write-Output "$($loc.Latitude),$($loc.Longitude)"; '
        '} else { '
        '  Write-Output "FAIL:$($GeoWatcher.Status):$($GeoWatcher.Permission)"; '
        '}'
    )
    
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        result = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=10,
            startupinfo=startupinfo
        )
        output = result.stdout.strip()
        if output and not output.startswith("FAIL"):
            return output
        else:
            print(f"Windows Location Service response: {output}")
    except Exception as e:
        print(f"Subprocess error: {e}")
    return None

gps = get_windows_gps()
print(f"Windows GPS Obtained: {gps}")
