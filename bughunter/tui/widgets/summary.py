from textual.widgets import Static, Label
from textual.containers import Vertical
from bughunter.models.event import BugHunterEvent

class ScoreSummaryWidget(Vertical):
    def compose(self):
        yield Label("Summary", classes="panel_title")
        self.stats = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0
        }
        self.labels = {}
        for k in self.stats.keys():
            lbl = Label(f"{k}: 0")
            self.labels[k] = lbl
            yield lbl

    def update_stats(self, event: BugHunterEvent):
        meta = event.metadata or {}
        severity = meta.get("severity", "").upper()
        if severity in self.stats:
            self.stats[severity] += 1
            self.labels[severity].update(f"{severity}: {self.stats[severity]}")
