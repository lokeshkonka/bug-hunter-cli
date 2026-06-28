from textual.widgets import Static, Label
from textual.containers import Vertical

class PhaseTrackerWidget(Vertical):
    def compose(self):
        yield Label("Phase Tracker", classes="panel_title")
        self.phase_label = Label("Initialization")
        yield self.phase_label

    def update_phase(self, phase: str):
        self.phase_label.update(f"Current: {phase}")
