from string import ascii_letters, digits

import requests
import whosyouragent
from pathier import Pathier

root = Pathier(__file__).parent


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
        response = requests.get(
            url, headers={"User-Agent": whosyouragent.get_agent()}, timeout=10
        )
        return get_board_type_from_text(response.text)
    except Exception as e:
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


def get_valid_urls(urls: list[str]) -> list[str] | None:
    """Make a request to each url in `urls`.

    Returns a list of the urls that return a 200 status code and don't redirect to a different url.
    """
    valid_urls = []
    for url in urls:
        try:
            response = requests.get(
                url, headers={"User-Agent": whosyouragent.get_agent()}, timeout=10
            )
            if response.status_code == 200 and response.url.strip("/") == url.strip(
                "/"
            ):
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
