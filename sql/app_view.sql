CREATE VIEW IF NOT EXISTS
    apps (
        a_id,
        l_id,
        rej,
        position,
        company,
        app_days,
        rej_days,
        alive,
        url
    ) AS
SELECT
    applications.application_id,
    applications.listing_id,
    CASE
        WHEN rejection_id IS NOT NULL THEN 1
        ELSE 0
    END,
    listings.position,
    companies.name,
    CAST(
        JULIANDAY ('now') - JULIANDAY (date_applied) AS INT
    ),
    CAST(
        JULIANDAY ('now') - JULIANDAY (date_rejected) AS INT
    ),
    listings.alive,
    listings.url
FROM
    applications
    INNER JOIN listings ON applications.listing_id = listings.listing_id
    INNER JOIN companies ON listings.company_id = companies.company_id
    LEFT JOIN rejections ON applications.application_id = rejections.application_id;