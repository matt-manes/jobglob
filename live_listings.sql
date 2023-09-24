SELECT
    listing_id,
    listings.position,
    companies.name AS company,
    listings.url,
    listings.date_added,
    CAST(
        JULIANDAY ('now') - JULIANDAY (listings.date_added) AS INT
    ) AS days_since_adding,
    listing_id IN (
        SELECT
            listing_id
        FROM
            applications
    ) AS applied
FROM
    listings
    INNER JOIN companies ON listings.company_id = companies.company_id
WHERE
    alive = 1
ORDER BY
    listings.date_added DESC;