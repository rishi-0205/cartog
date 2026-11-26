# PATTERN: CONFIG-FEATURE-01 — conditional command registration
import os
if os.environ.get("FEATURE_X"): app.command()(x)
