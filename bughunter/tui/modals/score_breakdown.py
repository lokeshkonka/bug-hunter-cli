from textual.screen import ModalScreen
from textual.widgets import Label, Button, Markdown
from textual.containers import Grid
from textual.app import ComposeResult

class ScoreBreakdownModal(ModalScreen):
    """Modal dialog for showing score breakdown."""
    
    CSS = """
    ScoreBreakdownModal {
        align: center middle;
    }
    
    #score_dialog {
        grid-size: 1;
        grid-gutter: 1 2;
        padding: 1 2;
        width: 80;
        height: 20;
        border: thick $background 80%;
        background: $surface;
    }
    """
    
    def __init__(self, finding_title: str, score_data: dict, **kwargs):
        super().__init__(**kwargs)
        self.finding_title = finding_title
        self.score_data = score_data

    def compose(self) -> ComposeResult:
        content = f"## {self.finding_title}\n\n"
        content += "| Component | Value | Weight | Points |\n"
        content += "|---|---|---|---|\n"
        content += f"| CVSS Base | {self.score_data.get('cvss', 0)} | 35% | ... |\n"
        content += f"| AI Confidence | {self.score_data.get('ai_prob', 0)} | 25% | ... |\n"
        content += f"| Evidence Weight | {self.score_data.get('evidence_weight', 0)} | 20% | ... |\n"
        content += f"| Exploit Factor | {self.score_data.get('exploit_factor', 0)} | 12% | ... |\n"
        content += f"| Remediation Penalty | {self.score_data.get('remed_penalty', 0)} | 8% | ... |\n"
        content += f"| **VulnScore** | | | **{self.score_data.get('vuln_score', 0)}** |\n"
        
        yield Grid(
            Markdown(content, id="score_content"),
            Button("Close", variant="primary", id="close_btn"),
            id="score_dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()
