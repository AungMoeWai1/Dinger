-- disable konnect payment provider
UPDATE payment_provider
   SET project_name=NULL,
       api_key = NULL,
       public_key = NULL,
       description = NULL,
       type = NULL;
DELETE FROM payment_method
WHERE id IN (
    (SELECT id
    FROM payment_method
    WHERE code IN ('bank', 'wallet', 'card')
    )
);
