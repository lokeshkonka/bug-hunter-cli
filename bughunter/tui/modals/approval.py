from textual.screen import ModalScreen
from textual.widgets import Label, Button
from textual.containers import Grid
from textual.app import ComposeResult

class ApprovalModal(ModalScreen[bool]):
    """Modal dialog for approving safe-active tests."""
    
    CSS = """
    ApprovalModal {
        align: center middle;
    }
    
    #dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: 1fr 3;
        padding: 0 1;
        width: 60;
        height: 11;
        border: thick $background 80%;
        background: $surface;
    }
    
    #question {
        column-span: 2;
        height: 1fr;
        width: 1fr;
        content-align: center middle;
    }
    
    Button {
        width: 100%;
    }
    """
    
    def __init__(self, message: str, **kwargs):
        super().__init__(**kwargs)
        self.message = message

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(self.message, id="question"),
            Button("Approve", variant="success", id="approve"),
            Button("Deny", variant="error", id="deny"),
            id="dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "approve":
            self.dismiss(True)
        else:
            self.dismiss(False)
