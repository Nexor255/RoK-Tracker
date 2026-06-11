import subprocess
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def detect_emulators() -> List[Dict[str, Any]]:
    """
    Detect running emulator instances by checking process list and open ports.
    Returns a list of dictionaries with 'id' (bluestacks/ld/memu/nox), 'name', and 'port'.
    """
    try:
        # 1. Get running processes
        # Use tasklist /FO CSV /NH to get CSV format with no header
        # Output looks like: "HD-Player.exe","24244","Console","1","50,116 K"
        tasks_out = subprocess.check_output("tasklist /FO CSV /NH", shell=True, stderr=subprocess.STDOUT)
        tasks = tasks_out.decode("utf-8", errors="ignore")
        
        pid_to_name = {}
        for line in tasks.strip().split("\n"):
            parts = line.split(",")
            if len(parts) >= 2:
                name = parts[0].strip('"')
                pid = parts[1].strip('"')
                pid_to_name[pid] = name

        # 2. Get active TCP connections to find listening ports on localhost
        netstat_out = subprocess.check_output("netstat -ano -p tcp", shell=True, stderr=subprocess.STDOUT)
        netstat = netstat_out.decode("utf-8", errors="ignore")
        
        # Emulator types mapping from executable name to id and display name
        emulator_types = {
            "HD-Player.exe": {"id": "bluestacks", "name": "BlueStacks"},
            "dnplayer.exe": {"id": "ld", "name": "LDPlayer"},
            "MEmuHeadless.exe": {"id": "memu", "name": "MEmu"},
            "MEmu.exe": {"id": "memu", "name": "MEmu"},
            "Nox.exe": {"id": "nox", "name": "Nox"},
            "NoxVMHandle.exe": {"id": "nox", "name": "Nox"},
        }
        
        emulators = []
        found_ports = set()
        
        for line in netstat.strip().split("\n"):
            parts = line.split()
            # Look for lines like: TCP    127.0.0.1:5555    0.0.0.0:0   LISTENING   24244
            if len(parts) >= 5 and parts[0] == "TCP" and parts[3] == "LISTENING":
                local_addr = parts[1]
                pid = parts[4]
                
                if local_addr.startswith("127.0.0.1:"):
                    try:
                        port = int(local_addr.split(":")[1])
                    except ValueError:
                        continue
                        
                    name = pid_to_name.get(pid, "")
                    
                    if name in emulator_types:
                        # Emulators might have multiple listening ports, filter to known ADB ranges
                        # BlueStacks/LDPlayer: 5550-5599
                        # MEmu: 21500-21599
                        # Nox: 62000-62099
                        if (5550 <= port <= 5599) or (21500 <= port <= 21599) or (62000 <= port <= 62099):
                            if port not in found_ports:
                                found_ports.add(port)
                                emulators.append({
                                    "id": emulator_types[name]["id"],
                                    "name": f"{emulator_types[name]['name']} ({port})",
                                    "port": port
                                })
        
        # Sort by port number for consistent ordering
        emulators.sort(key=lambda x: x["port"])
        return emulators
        
    except Exception as e:
        logger.error(f"Failed to detect emulators: {e}")
        return []
