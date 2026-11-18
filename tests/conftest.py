import ctypes
import os

for _candidate in (
    "/usr/local/aws-cli/v2/2.27.11/dist/libsqlite3.so.0",
    "/usr/local/aws-cli/v2/current/dist/libsqlite3.so.0",
):
    if os.path.exists(_candidate):
        try:
            ctypes.CDLL(_candidate, mode=ctypes.RTLD_GLOBAL)
            break
        except OSError:
            pass

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
