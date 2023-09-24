SELECT
    application_id,
    applications.listing_id,
    listings.position,
    companies.name AS company,
    listings.alive,
    rejected,
    CAST(
        JULIANDAY ('now') - JULIANDAY (date_applied) AS INT
    ) AS days_since_applying,
    CAST(
        JULIANDAY ('now') - JULIANDAY (date_rejected) AS INT
    ) AS days_since_rejected
FROM
    applications
    INNER JOIN listings ON applications.listing_id = listings.listing_id
    INNER JOIN companies ON listings.company_id = companies.company_id
ORDER BY
    rejected DESC,
    date_applied;