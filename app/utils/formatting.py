import re
def seconds_to_hms(seconds):
    """Converts seconds (float/int) into HH:MM:SS format."""
    try:
        total_seconds = float(seconds)
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        secs = int(total_seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    except (ValueError, TypeError):
        return f"{seconds}s"
def format_log_message(msg):
    """Parses logs to replace [123.45s -> 126.45s] with [HH:MM:SS -> HH:MM:SS]."""
    # Regex pattern to match specific seconds format provided by user context
    pattern = r"\[(\d+(?:\.\d+)?)s -> (\d+(?:\.\d+)?)s\]"
    def replace_match(match):
        start = seconds_to_hms(match.group(1))
        end = seconds_to_hms(match.group(2))
        return f"[{start} -> {end}]"
    return re.sub(pattern, replace_match, msg)
