CREATE VIEW IF NOT EXISTS
    scrapers (b_id, c_id, company, url, dob) AS
SELECT
    boards.board_id,
    companies.company_id,
    companies.name,
    boards.url,
    boards.date_added
FROM
    companies
    INNER JOIN boards ON companies.company_id = boards.company_id;