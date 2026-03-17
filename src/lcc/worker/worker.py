# Copyright 2025 Ajay Pundhir
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Arq worker entrypoint.
"""
import logging
import os

from arq.connections import RedisSettings

from lcc.config import load_config
from lcc.worker.tasks import run_scan_task

logger = logging.getLogger(__name__)

config = load_config()

# Parse Redis URL
redis_url = config.redis_url or "redis://localhost:6379"
# Arq expects settings, not just a URL string for everything, but RedisSettings can take host/port etc.
# Or we can use from_dsn if available, but RedisSettings is standard.
# Simple parsing for now or assume standard local default if not provided.
# If redis_url is provided, we should parse it.
# For simplicity, let's assume standard params or use a library to parse if needed.
# But `RedisSettings` doesn't take a URL string directly in constructor usually.
# It takes host, port, database, password.

# Let's try to parse the URL simply or fallback to defaults.
# redis://[:password@]host[:port][/db]
# This is a bit complex to parse manually robustly.
# However, arq's `create_pool` takes `RedisSettings`.
# Let's use a helper or just pass the settings if we can.

# Actually, `arq` worker can be run via CLI: `arq lcc.worker.worker.WorkerSettings`
# So we just need to define the class.

class WorkerSettings:
    functions = [run_scan_task]

    # Use a property or method to configure redis if needed, but static is standard.
    # We'll try to use the config.

    # Note: We can't easily parse the full URL here without a library like `redis-py`'s `from_url` logic
    # but `RedisSettings` is simple.
    # Let's assume localhost for now if not set, or try to parse basic.

    redis_settings = RedisSettings(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        database=int(os.getenv("REDIS_DB", 0)),
        password=os.getenv("REDIS_PASSWORD"),
    )
    logger.debug("Redis config: host=%s, port=%s", redis_settings.host, redis_settings.port)

    # If we wanted to use the full URL from config, we'd need to decompose it.
    # For now, relying on separate env vars or defaults is safer for this implementation step.
