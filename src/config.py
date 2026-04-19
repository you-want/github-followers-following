import logging
import os
import sys
from pathlib import Path

import structlog
import yaml
from dotenv import load_dotenv

load_dotenv()


def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
        handlers=[
            logging.FileHandler(log_dir / "app.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def get_github_token() -> str:
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token

    # Try reading from gh cli hosts.yml
    gh_hosts_path = Path.home() / ".config" / "gh" / "hosts.yml"
    if gh_hosts_path.exists():
        try:
            with open(gh_hosts_path, "r") as f:
                hosts = yaml.safe_load(f)
                if "github.com" in hosts and "oauth_token" in hosts["github.com"]:
                    return hosts["github.com"]["oauth_token"]
        except Exception:
            pass
    return ""


GITHUB_TOKEN = get_github_token()
