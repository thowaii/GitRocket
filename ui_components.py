# ui_components.py
import flet as ft
import re

class InteractiveDiffView(ft.Column):
    def __init__(self, diff_text, is_staged, on_apply):
        super().__init__()
        self.diff_text = diff_text
        self.is_staged = is_staged
        self.on_apply = on_apply
        self.hunks = []
        self.scroll = ft.ScrollMode.ADAPTIVE
        self._build_view()

    def _parse_hunks(self):
        lines = self.diff_text.split('\n')
        if not lines: return [], ""
        header_lines, line_idx = [], 0
        for i, line in enumerate(lines):
            if line.startswith('@@'):
                line_idx = i
                break
            header_lines.append(line)
        file_header = "\n".join(header_lines)
        parsed_hunks, current_hunk = [], []
        for line in lines[line_idx:]:
            if line.startswith('@@') and current_hunk:
                parsed_hunks.append("\n".join(current_hunk))
                current_hunk = [line]
            else:
                current_hunk.append(line)
        if current_hunk: parsed_hunks.append("\n".join(current_hunk))
        return parsed_hunks, file_header

    def _build_view(self):
        self.controls.clear()
        hunk_strings, self.file_header = self._parse_hunks()
        if not hunk_strings:
            self.controls.append(ft.Text("No changes to display."))
            return
        for hunk_text in hunk_strings:
            spans = []
            for line in hunk_text.split('\n'):
                color = "black87"
                if line.startswith('+'): color = "green_700"
                elif line.startswith('-'): color = "red_700"
                elif line.startswith('@@'): color = "blue_grey_400"
                spans.append(ft.TextSpan(f"{line}\n", ft.TextStyle(font_family="monospace", color=color)))
            checkbox = ft.Checkbox()
            self.hunks.append((checkbox, hunk_text))
            self.controls.append(ft.Card(ft.Row([checkbox, ft.Text(spans=spans, selectable=True, expand=True)]), elevation=1, margin=ft.margin.only(bottom=5)))
        button_text = "Unstage Selected" if self.is_staged else "Stage Selected"
        # CORRECTED: Use string literals for icon names
        button_icon = "remove" if self.is_staged else "add"
        apply_button = ft.ElevatedButton(button_text, icon=button_icon, on_click=self._handle_apply_click)
        self.controls.insert(0, ft.Container(apply_button, alignment=ft.alignment.center_right, margin=ft.margin.only(bottom=10)))

    async def _handle_apply_click(self, e):
        selected_hunks = [hunk_text for chk, hunk_text in self.hunks if chk.value]
        if not selected_hunks: return
        patch_content = self.file_header + "\n" + "\n".join(selected_hunks)
        await self.on_apply(patch_content)

class CommitComposer(ft.Column):
    """A guided component for writing conventional commit messages."""
    def __init__(self, on_suggest, on_commit, on_back):
        super().__init__()
        self.on_suggest = on_suggest
        self.on_commit = on_commit
        self.on_back = on_back
        
        self.commit_type = ft.Dropdown(
            label="Type", hint_text="Select commit type",
            options=[
                ft.dropdown.Option("feat"), ft.dropdown.Option("fix"), ft.dropdown.Option("docs"),
                ft.dropdown.Option("style"), ft.dropdown.Option("refactor"), ft.dropdown.Option("test"),
                ft.dropdown.Option("chore"), ft.dropdown.Option("merge"),
            ], width=200,
        )
        self.scope = ft.TextField(label="Scope (Optional)", width=200)
        self.subject = ft.TextField(label="Subject", hint_text="Concise summary of changes", expand=True)
        self.body = ft.TextField(label="Body (Optional)", hint_text="More detailed explanation...", multiline=True, min_lines=5)
        self.footer = ft.TextField(label="Footer (Optional)", hint_text="e.g., Closes #123")
        
        # CORRECTED: Use string literals for icon names
        self.ai_button = ft.OutlinedButton("AI Suggest", icon="auto_awesome", on_click=self.on_suggest)
        self.commit_button = ft.FilledButton("Commit & Launch", icon="rocket_launch", on_click=self._handle_commit)
        self.back_button = ft.IconButton(icon="arrow_back", on_click=self.on_back, tooltip="Back to Staging")

        self.controls = [
            ft.Row([
                self.back_button,
                ft.Text("Compose Commit Message", size=24, weight=ft.FontWeight.BOLD),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([self.commit_type, self.scope]),
            self.subject,
            self.body,
            self.footer,
            ft.Row([self.ai_button, self.commit_button], alignment=ft.MainAxisAlignment.END, spacing=10)
        ]

    async def _handle_commit(self, e):
        if self.commit_type.disabled: 
            message = self.subject.value
            if self.body.value: message += f"\n\n{self.body.value}"
            if self.footer.value: message += f"\n\n{self.footer.value}"
            await self.on_commit(message)
            return

        if not self.commit_type.value or not self.subject.value:
            self.subject.error_text = "Type and Subject are required!"
            self.subject.update()
            return
        
        header = f"{self.commit_type.value}({self.scope.value}): {self.subject.value}" if self.scope.value else f"{self.commit_type.value}: {self.subject.value}"
        message = header
        if self.body.value: message += f"\n\n{self.body.value}"
        if self.footer.value: message += f"\n\n{self.footer.value}"
        await self.on_commit(message)

    def populate_merge_message(self, message: str):
        self.reset_fields()
        lines = message.strip().split('\n')
        self.subject.value = lines[0]
        if len(lines) > 1:
            self.body.value = '\n'.join(lines[1:]).strip()
        
        self.commit_type.value = "merge"
        self.commit_type.disabled = True
        self.scope.disabled = True
        self.ai_button.disabled = True

    def populate_from_suggestion(self, suggestion):
        self.reset_fields()
        try:
            lines = suggestion.strip().split('\n\n')
            header = lines[0]
            commit_type_match = re.match(r"(\w+)", header)
            if commit_type_match: self.commit_type.value = commit_type_match.group(1)
            scope_match = re.search(r"\((.*?)\)", header)
            if scope_match:
                self.scope.value = scope_match.group(1)
                subject_part = header.split("):", 1)
                self.subject.value = subject_part[1].strip() if len(subject_part) > 1 else ""
            else:
                subject_part = header.split(":", 1)
                self.subject.value = subject_part[1].strip() if len(subject_part) > 1 else ""
            if len(lines) > 1: self.body.value = '\n\n'.join(lines[1:])
        except Exception as e:
            logging.error(f"Error parsing AI suggestion: {e}")
            self.subject.value = "AI suggestion (could not parse fully):"
            self.body.value = suggestion

    def reset_fields(self):
        for field in [self.commit_type, self.scope, self.subject, self.body, self.footer]:
            field.value = ""
            field.disabled = False
            field.error_text = None
        self.ai_button.disabled = False