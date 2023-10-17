from string import ascii_letters, digits

import requests
import whosyouragent
from pathier import Pathier
from printbuddies import PoolBar
from scrapetools import LinkScraper
from younotyou import younotyou
import quickpool

root = Pathier(__file__).parent


def request(url: str) -> requests.Response:
    return requests.get(
        url, headers={"User-Agent": whosyouragent.get_agent()}, timeout=10
    )


def load_meta() -> dict:
    """Load `board_meta.toml`."""
    return (root / "board_meta.toml").loads()


def get_url_chunks() -> dict:
    """Get url chunk to board type mapping."""
    return load_meta()["url_chunks"]


def get_url_templates() -> dict:
    """Get board type to url template mapping."""
    return load_meta()["url_templates"]


def get_board_type_from_text(text: str) -> str | None:
    """Returns the board type from `text`, or `None` if `text` doesn't match any chunks in `board_meta.toml`."""
    url_chunks = get_url_chunks()
    for chunk in url_chunks:
        if chunk in text:
            return url_chunks[chunk]
    return None


def get_board_type_from_page(url: str) -> str | None:
    """Makes a request to `url` and scans the returned content to determine the board type.

    Returns `None` if the board type could not be detected."""
    try:
        response = request(url)
        return get_board_type_from_text(response.text)
    except Exception as e:
        print(e)
        return None


def get_company_url_stems(company: str) -> list[str]:
    """Returns permutations of a company name to try in a url.

    e.g. "Company Inc." returns
    "companyinc"
    "company-inc"
    "company inc"
    "CompanyInc"
    """
    alphanum = ascii_letters + digits + " -"
    stems = [company]
    company_parts = company.split()
    stems.extend(["".join(company_parts), "-".join(company_parts)])
    stems.extend([stem.lower() for stem in stems])
    stems.extend(["".join(ch for ch in stem if ch in alphanum) for stem in stems])
    return list(set(stems))


def get_candidate_urls(company: str, board_type: str) -> list[str]:
    """Returns a list of potentially valid urls given a `company` and a `board_type`."""
    template_url = get_url_templates()[board_type]
    stems = get_company_url_stems(company)
    return [template_url.replace("$company", stem) for stem in stems]


def get_board_by_trial_and_error(company: str) -> list[str]:
    """Just try all the templates for a company name and see what sticks.

    >>> yeet"""
    url_templates = get_url_templates()
    board_types = list(url_templates.keys())
    candidate_urls = []

    def trial_error(company: str, board_type: str) -> list[str] | None:
        return get_valid_urls(get_candidate_urls(company, board_type))

    pool = PoolBar(
        "thread",
        [trial_error] * len(board_types),  # type: ignore
        [(company, board_type) for board_type in board_types],
    )
    results = pool.execute()
    for result in results:
        if result:
            candidate_urls.extend(result)
    return candidate_urls


def response_is_valid(response: requests.Response, requested_url: str) -> bool:
    return True if response.status_code == 200 and response.url.strip("/") == requested_url else False  # type: ignore


def get_valid_urls(urls: list[str]) -> list[str] | None:
    """Make a request to each url in `urls`.

    Returns a list of the urls that return a 200 status code and don't redirect to a different url.
    """
    valid_urls = []
    for url in urls:
        try:
            response = request(url)
            if response_is_valid(response, url) and (
                "ashbyhq.com" not in url
                or '"organization":null' not in response.text.lower()
            ):  # ashby returns a 200 even if the company doesn't exist with them
                valid_urls.append(url)
        except Exception as e:
            ...
    # Some are case sensitive and some aren't, return one lower case for those that appear case insensitive
    if len(valid_urls) == 2 and valid_urls[0].lower() == valid_urls[1].lower():
        valid_urls = [valid_urls[0].lower()]
    return valid_urls or None


def get_board_url(company: str, company_jobs_url: str) -> list[str] | None:
    """Attempt to determine the 3rd party job board url from a company's job page.

    Returns a list of valid urls or `None` if the board url could not be determined."""
    board_type = get_board_type_from_page(company_jobs_url)
    if not board_type:
        return None
    return get_valid_urls(get_candidate_urls(company, board_type))


def get_board_from_links(url: str) -> list[str]:
    """Make a request to `url` and search the page for possible job board links."""
    try:
        response = request(url)
    except Exception as e:
        return []
    linkscraper = LinkScraper(response.text, url)
    linkscraper.scrape_page()
    links = linkscraper.get_links(excluded_links=linkscraper.get_links("img"))
    boards = [f"*{board}*" for board in load_meta()["boards"]]
    urls = younotyou(links, boards, case_sensitive=False)
    return urls


def brute_force_careers_page(base_url: str) -> list[str]:
    """Returns a list of urls that returned a 200 code and didn't redirect."""
    base_url = base_url.strip("/")
    pages = (root / "careers_page_list.txt").split()
    urls = [f"{base_url}/{page}" for page in pages]
    results = quickpool.ThreadPool(
        [request] * len(urls), [(url,) for url in urls]
    ).execute(False)
    return [
        url for url, response in zip(urls, results) if response_is_valid(response, url)
    ]
