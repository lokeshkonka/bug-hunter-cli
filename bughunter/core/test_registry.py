import os
import json
import glob
from pathlib import Path

class TestRegistry:
    def __init__(self, plugins_dir: str = "~/.bughunter/plugins"):
        self.plugins_dir = Path(plugins_dir).expanduser()
        self.tests = []
        self.plugins = []

    def load_plugins(self):
        if not self.plugins_dir.exists():
            return
            
        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue
                
            plugin_json_path = plugin_dir / "plugin.json"
            if not plugin_json_path.exists():
                continue
                
            try:
                with open(plugin_json_path, "r") as f:
                    plugin_metadata = json.load(f)
                    
                self.plugins.append(plugin_metadata)
                
                # Load test files
                for test_pattern in plugin_metadata.get("tests", []):
                    search_pattern = str(plugin_dir / test_pattern)
                    for test_file in glob.glob(search_pattern):
                        with open(test_file, "r") as tf:
                            self.tests.append({
                                "plugin": plugin_metadata.get("name"),
                                "file": test_file,
                                "content": tf.read()
                            })
            except Exception as e:
                # Log error in real app
                pass

    def get_all_tests(self):
        return self.tests
