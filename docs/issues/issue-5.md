# Record the currency on payment charges (#5)

Finance needs to know which currency each charge was made in. Give every `Charge` recorded by the `PaymentGateway` a `currency` (ISO code, default `"USD"`), and let callers of `charge()` pass a different currency explicitly. Add tests.
