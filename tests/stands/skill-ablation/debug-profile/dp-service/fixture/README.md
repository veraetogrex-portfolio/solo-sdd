# Nightly sales import

Runs at 02:00 every night in three stages: `fetch` reads the shop's orders of the current month, `transform` keeps the rows of the configured period and converts the currency, `load` writes the rows to the `sales` table the dashboard reads. Each stage writes its log into `logs/`. The deployed commit is in `deploy.txt`.
