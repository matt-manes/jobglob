SELECT
    listing_id,
    listings.position,
    companies.name,
    listings.url,
    listings.date_added,
    CAST(
        JULIANDAY ('now') - JULIANDAY (listings.date_added) AS INT
    ),
    listing_id in (
        SELECT
            listing_id
        FROM
            applications
    )
FROM
    listings
    INNER JOIN companies ON listings.company_id = companies.company_id
WHERE
    alive = 1
ORDER BY
    listings.date_added DESC;