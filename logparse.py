import re

from pathier import Pathier

root = Pathier(__file__).parent


def get_log_path(company: str) -> Pathier:
    """Returns the path to the log file from a given `company` name."""
    company = company.lower().replace(" ", "_")
    return root / "logs" / f"{company}.log"


def get_last_log(company: str) -> str:
    """Returns the last log message for a given `company`."""
    lines = get_log_path(company).split()[::-1]
    log = []
    for line in lines:
        log.append(line)
        if re.findall(r"[a-zA-Z]+\|\-\|[a-zA-Z0-9/: ]+\|\-\|.+", line):
            break
    return "\n".join(log[::-1])


def get_parse_counts(company: str) -> tuple[int, int] | None:
    """Returns the number of successes and failures from the last scrape for a given `company` as tuple, success count first.

    Returns `None` if the last message isn't a `Scrape completed ... x successes and y failures` message."""
    last_log = get_last_log(company)
    if not last_log.startswith("INFO"):
        return None
    counts = re.findall(r"([0-9]+) successes and ([0-9]+) failures", last_log)
    if not counts:
        return None
    return (int(counts[0][0]), int(counts[0][1]))


def get_failed_scrapers() -> list[str]:
    """Returns a list of scrapers whose last log message is an `ERROR` or `EXCEPTION`."""
    fails = []
    for log in (root / "logs").glob("*.log"):
        last_log = get_last_log(log.stem)
        if last_log[: last_log.find("|")] in ["ERROR", "EXCEPTION"]:
            fails.append(log.with_suffix(".py").name)
    return fails


if __name__ == "__main__":
    print(*get_failed_scrapers(), sep="\n")
