# PATTERN: CONFIG-ENV-01 — env-var channel name (abstain)
import os
CHANNEL = os.environ.get("CHANNEL", "default")
def pub(data): r.publish(CHANNEL, data)
