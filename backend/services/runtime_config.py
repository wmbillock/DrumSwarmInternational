"""Runtime configuration with defaults, env overrides, and CLI overrides.

Precedence: CLI flag > env var > default.
"""

import os

DEFAULT_TIMEOUT = 300
DEFAULT_MAX_ITERATIONS = 30


def get_runtime_config(
    cli_timeout: int | None = None,
    cli_max_iterations: int | None = None,
) -> dict:
    """Return effective runtime config dict.

    Precedence: cli arg > env var > default.
    """
    # Timeout
    timeout = DEFAULT_TIMEOUT
    env_timeout = os.environ.get("DSI_LLM_TIMEOUT_SECONDS")
    if env_timeout:
        try:
            timeout = int(env_timeout)
        except ValueError:
            pass
    if cli_timeout is not None:
        timeout = cli_timeout

    # Max iterations
    max_iterations = DEFAULT_MAX_ITERATIONS
    env_iters = os.environ.get("DSI_MAX_ITERATIONS")
    if env_iters:
        try:
            max_iterations = int(env_iters)
        except ValueError:
            pass
    if cli_max_iterations is not None:
        max_iterations = cli_max_iterations

    return {
        "timeout": timeout,
        "max_iterations": max_iterations,
    }
