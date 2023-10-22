CREATE VIEW IF NOT EXISTS
    pinned (
        l_id,
        a_id,
        position,
        company,
        url,
        date_added,
        age_days,
        alive
    ) AS
SELECT
    listings.listing_id,
    applications.application_id,
    listings.position,
    companies.name,
    listings.url,
    listings.date_added,
    CAST(
        JULIANDAY ('now') - JULIANDAY (listings.date_added) AS INT
    ),
    listings.alive
FROM
    pinned_listings
    INNER JOIN listings ON pinned_listings.listing_id = listings.listing_id
    INNER JOIN companies ON listings.company_id = companies.company_id
    LEFT JOIN applications ON listings.listing_id = applications.listing_id;