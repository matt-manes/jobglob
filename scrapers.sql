CREATE VIEW IF NOT EXISTS
    scrapers (board_id, company_id, company, url) AS
SELECT
    scrapable_boards.board_id,
    companies.name,
    scrapable_boards.url
FROM
    scrapable_boards
    INNER JOIN companies ON scrapable_boards.board_id = companies.board_id;