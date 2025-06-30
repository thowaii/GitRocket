# main.py
import flet as ft
import os
import asyncio
import sys
import logging
import subprocess
from typing import Coroutine
import google.generativeai as genai
from dotenv import load_dotenv
from git_ops import GitRepository
from ui_components import InteractiveDiffView, CommitComposer

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("gitrocket.log"),
        logging.StreamHandler()
    ]
)

# --- Environment and AI Setup ---
load_dotenv()
gemini_model = None

def configure_ai():
    """Configures the Gemini client and returns the model."""
    global gemini_model
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logging.warning("GEMINI_API_KEY not found in .env. AI features will be disabled.")
        return None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        logging.info("Gemini AI configured successfully.")
        return model
    except Exception as e:
        logging.error(f"Failed to configure Gemini AI: {e}")
        return None

gemini_model = configure_ai()

def validate_environment():
    """Check all prerequisites before app starts"""
    checks = []
    logging.info("--- Validating Environment ---")
    
    # Check Git installation
    try:
        result = subprocess.run(['git', '--version'], capture_output=True, check=True, text=True)
        logging.info(f"Git validation successful: {result.stdout.strip()}")
        checks.append(("Git Installed", True, result.stdout.strip()))
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        logging.error(f"Git validation failed: {e}")
        checks.append(("Git Installed", False, "Git not found in system PATH."))
    
    # Check .env file and GEMINI_API_KEY
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logging.warning(".env file or GEMINI_API_KEY not found.")
        checks.append((".env Configuration", False, "Create .env with GEMINI_API_KEY for AI features."))
    else:
        logging.info(".env file with GEMINI_API_KEY found.")
        checks.append((".env Configuration", True, "GEMINI_API_KEY is set."))
    logging.info("--- Environment Validation Complete ---")
    return checks

class GitRocketApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "GitRocket - Mission Control"
        self.page.vertical_alignment = ft.MainAxisAlignment.CENTER
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.page.theme_mode = ft.ThemeMode.LIGHT
        
        self.repo: GitRepository | None = None
        self.current_view_container = ft.Column(expand=True, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.page.add(self.current_view_container)
        
        self.show_welcome_view()
        self.page.on_connect = self.load_last_project
        
    async def run_git_op(self, func, *args):
        return await self.page.loop.run_in_executor(None, func, *args)

    def show_error(self, message: str):
        logging.error(f"Displaying error to user: {message}")
        self.page.snack_bar = ft.SnackBar(ft.Text(f"Error: {message}", color="white"), open=True, bgcolor="red700")
        self.page.update()

    async def load_last_project(self, e):
        last_path = await self.page.client_storage.get_async("gitrocket.last_path")
        if last_path and os.path.exists(last_path):
            logging.info(f"Found last project path: {last_path}")
            await self.open_repo(last_path)
        else:
            logging.info("No last project path found.")
        
    async def open_repo(self, path):
        logging.info(f"Attempting to open repository at: {path}")
        try:
            self.repo = GitRepository(path)
            await self.page.client_storage.set_async("gitrocket.last_path", path)
            logging.info(f"Successfully opened repository: {path}")

            user_name_val = await self.run_git_op(self.repo.get_git_config, "user.name")
            user_email_val = await self.run_git_op(self.repo.get_git_config, "user.email")

            if not user_name_val or not user_email_val:
                logging.warning("Git user.name or user.email is not configured. Forcing user to settings.")

                async def go_to_settings(e):
                    await self.close_dialog()
                    await self.show_settings_view()

                self.page.dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Git Configuration Needed"),
                    content=ft.Text("Your user name and/or email are not set. This is required to make commits."),
                    actions=[ft.ElevatedButton("Go to Settings", on_click=go_to_settings)],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
                self.page.dialog.open = True
                self.page.update()
                return 

            if self.repo.in_merge_state:
                logging.warning("Repository is in a merge state.")
                conflicting_files = await self.run_git_op(self.repo.get_conflicting_files)
                await self.show_merge_conflict_view(conflicting_files)
            else:
                await self.show_dashboard()

        except (ValueError, RuntimeError) as err:
            logging.error(f"Failed to open repository at {path}: {err}")
            self.show_error(str(err))
            self.show_welcome_view()

    async def pick_folder_result(self, e: ft.FilePickerResultEvent):
        if e.path: await self.open_repo(e.path)

    def change_project(self, e):
        self.folder_picker.get_directory_path()

    def set_view(self, view: ft.Control):
        self.current_view_container.controls = [view]
        self.page.update()

    def show_welcome_view(self):
        self.folder_picker = ft.FilePicker(on_result=self.pick_folder_result)
        self.page.overlay.clear()
        self.page.overlay.append(self.folder_picker)
        checks = validate_environment()
        all_ok = all(c[1] for c in checks if c[0] == "Git Installed")
        check_list_items = []
        for name, success, message in checks:
            icon_name = "check_circle" if success else "cancel"
            color = "green" if success else "red"
            if name == ".env Configuration" and not success:
                color = "orange"
                icon_name = "warning"
            check_list_items.append(ft.Row([ft.Icon(name=icon_name, color=color), ft.Text(f"{name}: {message if not success else 'OK'}")]))
        welcome_view = ft.Column([
            ft.Text("🚀", size=80),
            ft.Text("GitRocket", size=40, weight=ft.FontWeight.BOLD),
            ft.Text("Welcome! Select a Git repository to get started."),
            ft.Divider(),
            ft.Text("System Checks", weight=ft.FontWeight.BOLD),
            *check_list_items,
            ft.Divider(),
            ft.FilledButton("Load Project Folder", icon="folder_open", on_click=lambda _: self.folder_picker.get_directory_path(), height=50, disabled=not all_ok)
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        self.set_view(welcome_view)

    async def _get_ai_suggestion_from_gemini(self):
        diff = await self.page.loop.run_in_executor(None, self.repo.get_file_diff, '.', True)
        if not diff: return None, "No staged changes to analyze."
        prompt = f"""Analyze the following git diff and generate a concise and conventional commit message. The format must be: type(scope): subject\n- The 'type' must be one of: feat, fix, docs, style, refactor, test, chore.\n- The 'scope' is optional. - The subject should be a short, imperative summary.\n- If necessary, add a blank line followed by a more detailed body explaining the 'why' and 'how'.\n- Do not include the diff in your response, only the commit message.\n--- DIFF ---\n{diff}"""
        response = await gemini_model.generate_content_async(prompt)
        return response.text, None

    async def run_ai_suggestion(self, e, max_retries=3):
        if gemini_model is None:
            self.show_error("AI features are disabled. Check GEMINI_API_KEY and logs.")
            return
        self.composer.ai_button.disabled = True
        self.composer.ai_button.text = "Thinking..."
        self.composer.update()
        for attempt in range(max_retries):
            try:
                logging.info(f"Requesting AI suggestion, attempt {attempt + 1}/{max_retries}")
                suggestion, error_message = await self._get_ai_suggestion_from_gemini()
                if error_message:
                    self.page.snack_bar = ft.SnackBar(ft.Text(error_message), open=True)
                    self.page.update()
                    break
                self.composer.populate_from_suggestion(suggestion)
                logging.info("Successfully received and populated AI suggestion.")
                break
            except Exception as ex:
                logging.error(f"AI suggestion attempt {attempt + 1} failed: {ex}")
                if attempt == max_retries - 1: self.show_error(f"AI service unavailable after {max_retries} attempts.")
                else: await asyncio.sleep(1)
        self.composer.ai_button.disabled = False
        self.composer.ai_button.text = "AI Suggest"
        self.composer.update()

    async def show_branch_management_view(self, e=None):
        branches_future = self.run_git_op(self.repo.get_branches)
        remotes_future = self.run_git_op(self.repo.get_remote_status)
        local_branches, remote_branches_list, current_branch = await branches_future
        remotes_dict = await remotes_future
        def create_branch_list(branches, is_remote=False):
            lv = ft.ListView(spacing=5, expand=True)
            for b in branches:
                is_current = (b == current_branch and not is_remote)
                controls = [ft.Text(b, expand=True, weight=("bold" if is_current else None), color=("blue" if is_current else None))]
                if not is_remote and not is_current: controls.extend([ft.ElevatedButton("Checkout", on_click=self.run_checkout, data=b), ft.OutlinedButton("Merge into current", on_click=self.run_merge, data=b)])
                lv.controls.append(ft.Row(controls))
            return lv
        remote_details = []
        for name, urls in remotes_dict.items():
            fetch_url = urls.get('fetch', 'N/A')
            remote_details.append(ft.Row([ft.Text(name, weight=ft.FontWeight.BOLD), ft.Text(fetch_url, selectable=True)]))
        branch_view = ft.Column([
            ft.Row([ft.IconButton(icon="arrow_back", on_click=self.show_dashboard), ft.Text("Branch Management", size=24, weight=ft.FontWeight.BOLD)], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([
                ft.Column([ft.Text("Local Branches", size=18), ft.Container(create_branch_list(local_branches), border=ft.border.all(1, "black26"), border_radius=5, padding=10, expand=True)], expand=1),
                ft.Column([
                    ft.Text("Remote Branches", size=18),
                    ft.Container(create_branch_list(remote_branches_list, is_remote=True), border=ft.border.all(1, "black26"), border_radius=5, padding=10, expand=True),
                    ft.Container(content=ft.Text("Remote URLs", size=16, weight=ft.FontWeight.BOLD), margin=ft.margin.only(top=10)),
                    *remote_details
                ], expand=1)
            ], expand=True)
        ], width=800, height=500)
        self.set_view(branch_view)

    async def show_dashboard(self, e=None):
        if not self.repo: return
        self.set_view(ft.Column([ft.ProgressRing(), ft.Text("Loading Dashboard...")], horizontal_alignment=ft.CrossAxisAlignment.CENTER))
        status_future = self.page.loop.run_in_executor(None, self.repo.get_branch_status)
        summary_future = self.page.loop.run_in_executor(None, self.repo.get_changes_summary)
        stashes_future = self.page.loop.run_in_executor(None, self.repo.get_stashes)
        history_future = self.page.loop.run_in_executor(None, self.repo.get_recent_history)
        branch_status, self.remote_branch_name = await status_future
        mod, new, d, staged_count = await summary_future
        stashes = await stashes_future
        history = await history_future
        header = ft.Row([ft.Text(self.repo.get_project_name(), size=32, weight=ft.FontWeight.BOLD), ft.Row([ft.IconButton(icon="sync", on_click=self.run_pull, tooltip="Sync with Remote"), ft.IconButton(icon="lan", on_click=self.show_branch_management_view, tooltip="Manage Branches"), ft.IconButton(icon="settings", on_click=self.show_settings_view, tooltip="Settings")])], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        path_text = ft.Text(self.repo.path, size=12, color="grey_600")
        status_text = ft.Text(branch_status, size=18)
        staged_text = ft.Text(f"🚀 {staged_count} Staged", color="green" if staged_count > 0 else None)
        overview = ft.Row([staged_text, ft.Text(f"📝 {mod} Modified"), ft.Text(f"✅ {new} New"), ft.Text(f"❌ {d} Deleted")], spacing=20)
        changes_count = mod + new + d + staged_count
        big_button = ft.ElevatedButton(f"Review {changes_count} Changes", icon="pageview", on_click=self.show_staging_view, height=50, disabled=(changes_count == 0))
        if changes_count == 0: big_button.text = "All Changes Committed"
        stash_list = ft.ListView(spacing=5, height=100, expand=True)
        if stashes:
            for s in stashes:
                stash_list.controls.append(ft.Row([ft.Text(s, expand=True, font_family="monospace"), ft.IconButton(icon="input", tooltip="Apply Stash", on_click=self.run_apply_stash, data=s), ft.IconButton(icon="delete_forever", tooltip="Delete Stash", on_click=self.run_drop_stash, data=s, icon_color="red")]))
        can_stash = mod + new + d > 0
        stash_tray = ft.Column([ft.Row([ft.Text("Stash Tray", weight=ft.FontWeight.BOLD), ft.ElevatedButton("Stash Changes", icon="archive", on_click=self.show_stash_dialog, disabled=not can_stash)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Container(content=stash_list, border=ft.border.all(1, "black26"), border_radius=5, padding=5, height=120) if stashes else ft.Text("No stashed changes.", italic=True)])
        history_list = ft.ListView(spacing=5, height=150)
        if history:
            for commit in history.splitlines():
                history_list.controls.append(ft.Text(commit, font_family="monospace"))
        dashboard_view = ft.Column([header, path_text, ft.Divider(), status_text, ft.Divider(), overview, big_button, ft.Divider(), stash_tray, ft.Divider(), ft.Text("Recent History", weight=ft.FontWeight.BOLD), history_list], spacing=15, width=800)
        self.set_view(dashboard_view)

    async def show_staging_view(self, e=None):
        self.unstaged_list = ft.ListView(expand=1, spacing=5)
        self.staged_list = ft.ListView(expand=1, spacing=5)
        self.diff_view_container = ft.Column([ft.Text("Click a file to see changes")], expand=2, scroll=ft.ScrollMode.ADAPTIVE)
        self.current_staging_event = None
        staging_view = ft.Column([ft.Row([ft.Text("Launchpad: Prepare Your Payload", size=24, weight=ft.FontWeight.BOLD), ft.Row([ft.ElevatedButton("Stage All", on_click=self.stage_all, icon="add_box"), ft.ElevatedButton("Unstage All", on_click=self.unstage_all, icon="indeterminate_check_box_outlined")])], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Row([ft.Column([ft.Text("Unstaged Changes", weight=ft.FontWeight.BOLD), self.unstaged_list], expand=1), ft.Column([ft.Text("Staged Changes (Your Payload)", weight=ft.FontWeight.BOLD), self.staged_list], expand=1)], expand=4), ft.Divider(), self.diff_view_container, ft.Row([ft.OutlinedButton("Back to Dashboard", icon="arrow_back", on_click=self.show_dashboard), ft.ElevatedButton("Compose Commit Message", icon="edit_note", on_click=self.handle_compose_click)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)], width=1000, height=700)
        self.set_view(staging_view)
        await self.update_staging_lists()

    async def update_staging_lists(self):
        file_limit = 200
        unstaged_files, staged_files = await asyncio.gather(
            self.page.loop.run_in_executor(None, self.repo.get_unstaged_files, file_limit),
            self.page.loop.run_in_executor(None, self.repo.get_staged_files, file_limit)
        )
        self.unstaged_list.controls.clear()
        for f in unstaged_files: self.unstaged_list.controls.append(ft.Row([ft.IconButton(icon="add_circle_outline", on_click=self.stage_file, data=f, tooltip="Stage file"), ft.TextButton(f, on_click=self.show_file_diff, data=(f, False))]))
        if len(unstaged_files) >= file_limit: self.unstaged_list.controls.append(ft.Text(f"...and more (display limit of {file_limit} reached)", italic=True, color="grey"))
        self.staged_list.controls.clear()
        for f in staged_files: self.staged_list.controls.append(ft.Row([ft.IconButton(icon="remove_circle_outline", on_click=self.unstage_file, data=f, tooltip="Unstage file"), ft.TextButton(f, on_click=self.show_file_diff, data=(f, True))]))
        if len(staged_files) >= file_limit: self.staged_list.controls.append(ft.Text(f"...and more (display limit of {file_limit} reached)", italic=True, color="grey"))
        self.page.update()
        
    async def show_settings_view(self, e=None):
        user_name_val = await self.run_git_op(self.repo.get_git_config, "user.name")
        user_email_val = await self.run_git_op(self.repo.get_git_config, "user.email")
        user_name_field = ft.TextField(label="User Name", value=user_name_val)
        user_email_field = ft.TextField(label="User Email", value=user_email_val)
        async def save_settings(e):
            if not user_name_field.value or not user_email_field.value:
                self.show_error("User Name and User Email cannot be empty.")
                return
            await self.run_git_op(self.repo.set_git_config, "user.name", user_name_field.value)
            await self.run_git_op(self.repo.set_git_config, "user.email", user_email_field.value)
            self.page.snack_bar = ft.SnackBar(ft.Text("Settings saved to local repo config."), open=True)
            await self.close_dialog()
            await self.show_dashboard()
        settings_view = ft.Column([ft.Row([ft.IconButton(icon="arrow_back", on_click=self.show_dashboard), ft.Text("Settings", size=24, weight=ft.FontWeight.BOLD)]), ft.Text("Git User (for this repository)"), user_name_field, user_email_field, ft.ElevatedButton("Save Settings", on_click=save_settings), ft.Divider(), ft.Text("Application"), ft.ElevatedButton("Change Project Folder", icon="folder_open", on_click=self.change_project)], width=600, spacing=15)
        self.set_view(settings_view)
    
    async def show_merge_conflict_view(self, conflicting_files):
        file_list = ft.ListView(spacing=5, expand=True)
        for f in conflicting_files: file_list.controls.append(ft.Text(f, font_family="monospace"))
        async def continue_after_resolve(e):
            merge_message = await self.run_git_op(self.repo.get_merge_message)
            self.composer = CommitComposer(on_suggest=self.run_ai_suggestion, on_commit=self.run_commit_and_push, on_back=self.show_dashboard)
            self.composer.populate_merge_message(merge_message)
            self.set_view(self.composer)
        conflict_view = ft.Column([ft.Text("🚨 MERGE CONFLICT 🚨", size=30, color="red", weight=ft.FontWeight.BOLD), ft.Text("Please resolve conflicts in your editor, then stage the resolved files ('git add .').", max_lines=3), ft.Container(content=file_list, border=ft.border.all(1, "black26"), border_radius=5, padding=10, expand=True), ft.Text("After resolving and staging, click Continue to finalize the merge commit."), ft.Row([ft.ElevatedButton("I have staged resolutions. Continue.", icon="check_circle", on_click=continue_after_resolve, bgcolor="green"), ft.ElevatedButton("Abort Merge", icon="cancel", on_click=self.run_abort_merge, bgcolor="red")], alignment=ft.MainAxisAlignment.CENTER)], width=800, height=500, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20)
        self.set_view(conflict_view)

    async def _pre_operation_check_and_run(self, operation_coro: Coroutine, operation_name: str):
        is_clean = await self.page.loop.run_in_executor(None, self.repo.is_working_directory_clean)
        if is_clean:
            await operation_coro
            return
        async def stash_and_continue(e):
            await self.close_dialog()
            stash_res = await self.run_git_op(self.repo.create_stash, f"Auto-stash before {operation_name}")
            if stash_res.success:
                self.page.snack_bar = ft.SnackBar(ft.Text("Changes stashed successfully."), open=True)
                self.page.update()
                await operation_coro
            else: self.show_error(f"Failed to stash changes: {stash_res.stderr}")
        dialog = ft.AlertDialog(
            modal=True, title=ft.Text("Uncommitted Changes Detected"),
            content=ft.Text(f"You have uncommitted changes. To prevent data loss, you can stash them before continuing the '{operation_name}' operation."),
            actions=[ft.ElevatedButton("Stash and Continue", on_click=stash_and_continue), ft.TextButton("Cancel", on_click=self.close_dialog)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    async def stage_file(self, e):
        res = await self.run_git_op(self.repo.stage_item, e.control.data)
        if not res.success: self.show_error(res.stderr)
        self.diff_view_container.controls = [ft.Text("Click a file to see changes")]
        await self.update_staging_lists()
        
    async def unstage_file(self, e):
        res = await self.run_git_op(self.repo.unstage_item, e.control.data)
        if not res.success: self.show_error(res.stderr)
        self.diff_view_container.controls = [ft.Text("Click a file to see changes")]
        await self.update_staging_lists()

    async def stage_all(self, e):
        res = await self.run_git_op(self.repo.stage_item, '.')
        if not res.success: self.show_error(res.stderr)
        await self.update_staging_lists()

    async def unstage_all(self, e):
        res = await self.run_git_op(self.repo.unstage_item, '.')
        if not res.success: self.show_error(res.stderr)
        await self.update_staging_lists()

    async def show_file_diff(self, e):
        self.current_staging_event = e
        file_path, is_staged = e.control.data
        diff_text = await self.page.loop.run_in_executor(None, self.repo.get_file_diff, file_path, is_staged)
        async def handle_apply(patch_content):
            result = await self.run_git_op(self.repo.apply_patch, patch_content, reverse=is_staged)
            if not result.success: self.show_error(f"Failed to apply patch: {result.stderr}")
            await self.update_staging_lists()
            await self.show_file_diff(self.current_staging_event)
        if not diff_text: self.diff_view_container.controls = [ft.Text("No changes to display for this file.")]
        else: self.diff_view_container.controls = [InteractiveDiffView(diff_text, is_staged, on_apply=handle_apply)]
        self.page.update()

    async def handle_compose_click(self, e):
        staged_files = await self.run_git_op(self.repo.get_staged_files)
        if not staged_files:
            self.page.snack_bar = ft.SnackBar(ft.Text("No files staged!"), open=True)
            self.page.update()
            return
        self.composer = CommitComposer(on_suggest=self.run_ai_suggestion, on_commit=self.run_commit_and_push, on_back=self.show_dashboard)
        self.set_view(self.composer)

    # --- START OF DEFINITIVE FIX ---
    # This method is now simplified. It directly calls the launch sequence, making the button atomic.
    # The confirmation dialog is removed as it was causing the workflow bug.
    async def run_commit_and_push(self, message):
        """Directly starts the launch sequence without a confirmation dialog."""
        await self.start_launch_sequence(message)
    # --- END OF DEFINITIVE FIX ---

    async def close_dialog(self, e=None):
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()

    async def start_launch_sequence(self, message):
        # We no longer need to close a dialog that doesn't exist.
        # await self.close_dialog()
        
        self.set_view(ft.Column([ft.ProgressRing(), ft.Text("Committing...")], horizontal_alignment=ft.CrossAxisAlignment.CENTER))
        commit_res = await self.run_git_op(self.repo.commit, message)
        if not commit_res.success:
            await self.show_launch_result(False, f"Commit failed:\n{commit_res.stderr}")
            return
        
        self.set_view(ft.Column([ft.ProgressRing(), ft.Text("Launching to remote...")], horizontal_alignment=ft.CrossAxisAlignment.CENTER))
        await asyncio.sleep(1) 
        push_res = await self.run_git_op(self.repo.push)
        if not push_res.success:
            await self.show_launch_result(False, f"Push failed:\n{push_res.stderr}")
            return
            
        await self.show_launch_result(True, push_res.stdout or push_res.stderr)
    
    async def show_launch_result(self, success, output):
        result_view = ft.Column(
            [
                ft.Text("✅" if success else "💥", size=80),
                ft.Text("Landed on Remote!" if success else "Launch Aborted!", size=30, weight=ft.FontWeight.BOLD),
                ft.Text("Details:", weight=ft.FontWeight.BOLD, visible=bool(output)),
                ft.Container(
                    content=ft.Text(output, font_family="monospace", selectable=True),
                    padding=10,
                    border=ft.border.all(1, "black12"),
                    border_radius=5,
                    visible=bool(output)
                ),
                ft.TextButton("Back to Dashboard", on_click=self.show_dashboard),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20, width=600
        )
        self.set_view(result_view)
        
    async def _do_pull(self):
        self.set_view(ft.Column([ft.ProgressRing(), ft.Text("Syncing with remote...")], horizontal_alignment=ft.CrossAxisAlignment.CENTER))
        pull_res = await self.run_git_op(self.repo.pull)
        if self.repo.in_merge_state:
            conflicting_files = await self.run_git_op(self.repo.get_conflicting_files)
            await self.show_merge_conflict_view(conflicting_files)
        elif not pull_res.success:
            self.show_error(f"Pull failed: {pull_res.stderr}")
            await self.show_dashboard()
        else:
            await self.show_dashboard()

    async def run_pull(self, e):
        await self._pre_operation_check_and_run(self._do_pull(), "pull")

    async def _do_checkout(self, branch):
        self.set_view(ft.Column([ft.ProgressRing(), ft.Text(f"Checking out {branch}...")], horizontal_alignment=ft.CrossAxisAlignment.CENTER))
        checkout_res = await self.run_git_op(self.repo.checkout_branch, branch)
        if not checkout_res.success: self.show_error(checkout_res.stderr)
        await self.show_dashboard()

    async def run_checkout(self, e):
        await self._pre_operation_check_and_run(self._do_checkout(e.control.data), "checkout")

    async def run_merge(self, e):
        branch_to_merge = e.control.data
        if not self.repo.validate_branch_name(branch_to_merge):
            self.show_error(f"Invalid branch name for merge: {branch_to_merge}")
            return
        merge_res = await self.run_git_op(self.repo.merge_branch, branch_to_merge)
        if self.repo.in_merge_state:
            conflicting_files = await self.run_git_op(self.repo.get_conflicting_files)
            await self.show_merge_conflict_view(conflicting_files)
        elif not merge_res.success:
            self.show_error(merge_res.stderr)
        await self.show_branch_management_view()
            
    async def run_abort_merge(self, e):
        await self.run_git_op(self.repo.abort_merge)
        await self.show_dashboard()

    async def show_stash_dialog(self, e):
        stash_message_field = ft.TextField(label="Stash Message (Optional)")
        async def do_stash(e_inner):
            await self.run_git_op(self.repo.create_stash, stash_message_field.value)
            await self.close_dialog()
            await self.show_dashboard()
        dlg = ft.AlertDialog(modal=True, title=ft.Text("Stash Current Changes"), content=stash_message_field, actions=[ft.ElevatedButton("Stash", on_click=do_stash), ft.TextButton("Cancel", on_click=self.close_dialog)])
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    async def run_apply_stash(self, e):
        res = await self.run_git_op(self.repo.apply_stash, e.control.data)
        if not res.success: self.show_error(res.stderr)
        await self.show_dashboard()

    async def run_drop_stash(self, e):
        await self.run_git_op(self.repo.drop_stash, e.control.data)
        await self.show_dashboard()

def main(page: ft.Page):
    """Main entry point with global crash handler."""
    try:
        app = GitRocketApp(page)
    except Exception as e:
        logging.critical(f"An unhandled exception occurred during app initialization: {e}", exc_info=True)
        error_view = ft.Column([
            ft.Icon(name="error", color="red", size=64),
            ft.Text("A Critical Error Occurred", size=32, weight=ft.FontWeight.BOLD),
            ft.Text("GitRocket has encountered a problem and cannot continue."),
            ft.Text("Please check the 'gitrocket.log' file for details."),
            ft.Container(
                content=ft.Text(f"{e}", font_family="monospace", selectable=True),
                padding=10,
                border=ft.border.all(1, "red400"),
                border_radius=5
            )
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)
        page.controls.clear()
        page.add(error_view)
        page.update()

if __name__ == "__main__":
    ft.app(target=main)