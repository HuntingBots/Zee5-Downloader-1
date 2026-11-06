def human_bytes(size: float) -> str:
    if not size or size < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size_f = float(size)
    while size_f >= 1024.0 and i < len(units) - 1:
        size_f /= 1024.0
        i += 1
    if i == 0:
        return f"{int(size_f)} B"
    return f"{size_f:.1f} {units[i]}"

def render_progress_bar(
    current: int,
    total: int,
    speed: float,
    eta: float,
    engine: str,
    mode: str = "DOWNLOAD",
    header: str = ""
) -> str:
    percent = (current / total * 100) if total > 0 else 0
    percent = min(100.0, max(0.0, percent))

    total_blocks = 10
    filled = int(round(percent / 10))
    filled = min(total_blocks, max(0, filled))
    bar = "█" * filled + "." * (total_blocks - filled)

    icon = "⬇️" if mode.upper() == "DOWNLOAD" else "⬆️"
    speed_str = f"{human_bytes(speed)}/s" if speed > 0 else "0 B/s"

    if eta <= 0 or eta > 86400:
        eta_str = "0s"
    elif eta < 60:
        eta_str = f"{int(eta)}s"
    elif eta < 3600:
        eta_str = f"{int(eta // 60)}m {int(eta % 60)}s"
    else:
        eta_str = f"{int(eta // 3600)}h {int((eta % 3600) // 60)}m"

    lines = []
    if header:
        lines.append(header)
        lines.append("")

    lines.append(f"{icon} {mode.upper()}  [{bar}] {int(round(percent))}%")
    lines.append(f"📦 {human_bytes(current)} / {human_bytes(total)}")
    lines.append(f"🚀 {speed_str} | ETA: {eta_str}")
    lines.append(f"⚙️ Engine: {engine}")

    return "\n".join(lines)
