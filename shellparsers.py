import argshell

import company_crawler


def get_add_listing_parser() -> argshell.ArgShellParser:
    """Returns an `add_listing` parser."""
    parser = argshell.ArgShellParser(prog="")
    parser.add_argument("position", type=str, help=" The job title of the listing. ")
    parser.add_argument("company", type=str, help=" The company the listing is for. ")
    parser.add_argument("url", type=str, help=" The url of the listing. ")
    parser.add_argument(
        "-l",
        "--location",
        type=str,
        default="Remote",
        help=' The location of the listing. Defaults to "Remote". ',
    )
    parser.add_argument(
        "-a", "--applied", action="store_true", help=" Mark this listing as 'applied'. "
    )
    return parser


def get_add_board_parser() -> argshell.ArgShellParser:
    """Returns a `add_board` parser."""
    parser = argshell.ArgShellParser()
    parser.add_argument("url", type=str, help=" Job board url.3 ")
    parser.add_argument("company", type=str, help=" Company name. ")
    parser.add_argument(
        "-b",
        "--board_type",
        type=str,
        default=None,
        help=" Specify a board type instead of trying to detect one. ",
    )
    return parser


def get_toggle_scraper_parser() -> argshell.ArgShellParser:
    """Returns a `toggle_scraper` parser."""
    parser = argshell.ArgShellParser(
        "toggle_scraper", description="Activate or deactivate scrapers/boards."
    )
    parser.add_argument(
        "status",
        choices=["a", "d"],
        type=str,
        default=None,
        help=" Whether the boards should be activated (a) or deactivated (d).",
    )
    parser.add_argument(
        "scrapers",
        nargs="*",
        type=str,
        default=[],
        help=" A list of board ids or company stems to toggle.",
    )
    return parser


def get_crawl_company_parser() -> argshell.ArgShellParser:
    """Returns a `crawl_company` parser."""
    parser = company_crawler.get_company_crawler_parser()
    parser.add_argument("homepage", type=str, help=" The url to start crawling at.")
    return parser


def get_update_board_url_parser() -> argshell.ArgShellParser:
    """Returns an `update_board_url` parser."""
    parser = argshell.ArgShellParser(
        prog="Update board url.", description="Update the specified board to a new url."
    )
    parser.add_argument("id", type=int, help=""" The id of the board to update""")
    parser.add_argument("url", type=str, help=""" The new url.""")
    return parser
