"""Example local narrator with no network request or API key."""


class ExampleNarrator:
    def render(self, notice, settings):
        return notice["message"]
