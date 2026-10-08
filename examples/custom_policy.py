"""Minimal extension example; not a validated notification policy."""


class ExamplePolicy:
    def select(self, report, state, as_of, settings):
        # Use the built-in policy as a safe starting point, then version any changes.
        from healthos.monitor import ConservativePolicy
        return ConservativePolicy().select(report, state, as_of, settings)
