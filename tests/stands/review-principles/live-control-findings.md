src/shop/payments.py:15 — bare `except:` around `gateway.post`; name the exception (rule 1).
src/shop/payments.py:5 — `charge` runs 20 lines (5-24), longer than 15; split it, for example into building the request and recording the payment (rule 8).
src/shop/payments.py:12 — `request["order"]` gets `order["user"]`, so the gateway receives the user and not the order id.
src/shop/payments.py:16 — a gateway error, and a status other than "ok" at line 19, both return the order unchanged with no error and no log; the caller cannot tell a failed charge from an order that was never charged.
Important: 4
