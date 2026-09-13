import psutil
from .system_collector import format_bytes


def get_top_processes(sort_by: str = "ram", limit: int = 10) -> dict:
    """
    Returns top processes sorted by RAM or CPU utilization.
    Guarded against AccessDenied and NoSuchProcess exceptions.
    """
    procs = []
    total_rss = 0
    total_procs_count = 0

    attrs = ['pid', 'name', 'username', 'memory_info', 'memory_percent', 'cpu_percent', 'cmdline']
    for proc in psutil.process_iter(attrs):
        total_procs_count += 1
        try:
            p_info = proc.info
            mem_info = p_info.get('memory_info')
            rss_bytes = mem_info.rss if mem_info else 0
            total_rss += rss_bytes

            # Command line formatting
            cmd_list = p_info.get('cmdline')
            if cmd_list and len(cmd_list) > 0:
                cmd_str = " ".join(cmd_list)
            else:
                cmd_str = p_info.get('name') or "unknown"

            # Username fallback
            user = p_info.get('username') or "system"
            if "\\" in user:
                user = user.split("\\")[-1]

            procs.append({
                "pid": p_info.get('pid'),
                "user": user,
                "name": p_info.get('name') or "unknown",
                "ram_rss_bytes": rss_bytes,
                "ram_rss_formatted": format_bytes(rss_bytes),
                "ram_percent": round(p_info.get('memory_percent') or 0.0, 1),
                "cpu_percent": round(p_info.get('cpu_percent') or 0.0, 1),
                "cmdline": cmd_str
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # Sort based on requested parameter
    if sort_by.lower() == "cpu":
        procs.sort(key=lambda x: (x["cpu_percent"], x["ram_rss_bytes"]), reverse=True)
    else:
        procs.sort(key=lambda x: (x["ram_rss_bytes"], x["cpu_percent"]), reverse=True)

    # Calculate total system memory for context
    try:
        vm = psutil.virtual_memory()
        ram_summary = f"{format_bytes(vm.used)} / {format_bytes(vm.total)}"
    except Exception:
        ram_summary = format_bytes(total_rss)

    return {
        "sort_by": sort_by.lower(),
        "limit": limit,
        "total_processes": total_procs_count,
        "ram_in_use_formatted": ram_summary,
        "processes": procs[:limit]
    }
