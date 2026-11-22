src/shop/payments.py:15 — Important: a bare `except:` breaks rule 1. It also catches KeyboardInterrupt and SystemExit. Name the gateway's exception instead.
src/shop/payments.py:16 — Important: when the gateway call fails, the code returns the order unchanged and reports nothing. The caller cannot tell a failed charge from a skipped one. Raise an error or return an explicit failure.
src/shop/payments.py:18 — Important: a declined charge (`status != "ok"`) is also dropped silently and the order comes back unpaid with no error. Raise an error or report the failure.
src/shop/payments.py:12 — Important: `request["order"]` is set to `order["user"]`, so the gateway gets the user instead of the order id. The payment cannot be traced back to its order.
src/shop/payments.py:5 — Important: nothing checks whether the order is already paid (`order["state"] == "paid"`), so calling `charge` again charges the card twice.
src/shop/payments.py:7 — Minor: rule 3 (integer cents) is not enforced. If `price` is ever a float, `amount` becomes a float and goes to the gateway. Assert or convert to int cents.
src/shop/payments.py:14 — Minor: the request is sent as a `json.dumps` string, but the reply on line 17 is read as a dict (`answer.get`). One of the two does not match the gateway client's contract.
src/shop/payments.py:11 — Minor: the currency is hard-coded to "EUR" and not taken from the order.
Important: 5
