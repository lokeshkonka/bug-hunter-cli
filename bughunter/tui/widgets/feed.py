from textual.widgets import RichLog
from textual.containers import Vertical
from bughunter.models.event import BugHunterEvent

class AgentFeedWidget(Vertical):
    def compose(self):
        yield RichLog(id="feed_log", highlight=True, markup=True)

    def on_mount(self):
        self.log_widget = self.query_one("#feed_log", RichLog)

    def add_event(self, event: BugHunterEvent):
        color = "cyan"
        if "error" in event.type: color = "red"
        elif "finding" in event.type: color = "magenta"
        
        self.log_widget.write(f"[{color}][{event.agent}][/] {event.message}")
