CREATE VIEW IF NOT EXISTS
    openings (
        l_id,
        c_id,
        position,
        location,
        company,
        url,
        alive,
        days
    ) AS
SELECT
    listings.listing_id,
    companies.company_id,
    position,
    location,
    companies.name,
    url,
    alive,
    CAST(
        JULIANDAY ('now') - JULIANDAY (listings.date_added) AS INT
    )
FROM
    listings
    INNER JOIN companies on listings.company_id = companies.company_id;