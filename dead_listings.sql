SELECT
    listing_id,
    listings.name,
    companies.name,
    listings.url,
    listings.date_added,
    CAST(
        JULIANDAY ('now') - JULIANDAY (listings.date_added) AS INT
    )
FROM
    listings
    INNER JOIN companies ON listings.company_id = companies.company_id
WHERE
    alive = 0
ORDER BY
    listings.date_added DESC;