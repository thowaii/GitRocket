# git_ops.py
import subprocess
import os
import re
import tempfile
import logging
from dataclasses import dataclass

@dataclass
class GitResult:
    success: bool
    stdout: str = ""
    stderr: str = ""

class GitRepository:
    def __init__(self, path):
        if not os.path.isdir(os.path.join(path, '.git')):
            raise ValueError("Not a Git repository ('.git' folder not found)")
        
        self.path = path
        if not os.access(path, os.R_OK | os.W_OK):
            raise ValueError("Insufficient read/write permissions for the repository path")

        self.in_merge_state = False
        
        test_result = self._run_command(['git', 'status', '--porcelain'])
        if not test_result.success and "not a git repository" in test_result.stderr.lower():
            raise ValueError("Folder contains '.git' but is not a valid repository")
            
        self.check_merge_status()

    def _run_command(self, command, input_data: str | None = None, timeout=30) -> GitResult:
        if not command or command[0] != 'git':
            logging.error(f"Security Error: Attempted to run non-git command: {command}")
            return GitResult(success=False, stderr="Security Error: Only 'git' commands are allowed")

        try:
            command_list = [str(c) for c in command if c]
            logging.info(f"Running command: {' '.join(command_list)}")
            result = subprocess.run(
                command_list, cwd=self.path, capture_output=True,
                text=True, check=False, encoding='utf-8', 
                input=input_data, timeout=timeout
            )
            self.check_merge_status()
            if result.returncode == 0:
                return GitResult(success=True, stdout=result.stdout.strip(), stderr=result.stderr.strip())
            else:
                logging.warning(f"Git command failed: {' '.join(command_list)}. Stderr: {result.stderr.strip()}")
                return GitResult(success=False, stdout=result.stdout.strip(), stderr=result.stderr.strip())
        except FileNotFoundError:
            logging.critical("Git executable not found in PATH.")
            raise RuntimeError("Git is not installed or not in your PATH.")
        except subprocess.TimeoutExpired:
            logging.error(f"Git command timed out: {' '.join(command)}")
            return GitResult(success=False, stderr=f"Git operation timed out after {timeout} seconds")
        except Exception as e:
            logging.error(f"An unexpected error occurred in _run_command: {e}")
            return GitResult(success=False, stderr=f"An unexpected error occurred: {e}")

    def validate_branch_name(self, branch_name: str) -> bool:
        if not branch_name or len(branch_name) > 100: return False
        if any(pattern in branch_name for pattern in ['..', '.lock', '@{', '\\']): return False
        if branch_name.startswith('-') or branch_name.endswith('.'): return False
        if any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in branch_name): return False
        if re.search(r'[\~^:?*\[]', branch_name): return False
        return True

    def get_remote_status(self) -> dict:
        remotes = {}
        result = self._run_command(['git', 'remote', '-v'])
        if result.success:
            for line in result.stdout.splitlines():
                match = re.match(r"(\S+)\s+(\S+)\s+\((fetch|push)\)", line)
                if match:
                    name, url, type = match.groups()
                    if name not in remotes: remotes[name] = {}
                    remotes[name][type] = url
        return remotes
    
    def check_merge_status(self):
        self.in_merge_state = os.path.exists(os.path.join(self.path, '.git', 'MERGE_HEAD'))
        return self.in_merge_state

    def is_working_directory_clean(self) -> bool:
        result = self._run_command(['git', 'status', '--porcelain'])
        return result.success and not result.stdout

    def get_merge_message(self) -> str:
        merge_msg_path = os.path.join(self.path, '.git', 'MERGE_MSG')
        if os.path.exists(merge_msg_path):
            try:
                with open(merge_msg_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except IOError: return "Could not read merge message."
        return ""
        
    def get_staged_files(self, limit=200) -> list[str]:
        result = self._run_command(['git', 'diff', '--name-only', '--cached'])
        files = result.stdout.splitlines() if result.success and result.stdout else []
        return files[:limit]

    def get_unstaged_files(self, limit=200) -> list[str]:
        result = self._run_command(['git', 'status', '--porcelain'])
        if not result.success: return []
        files = []
        for line in result.stdout.splitlines():
            if not line: continue
            if line.startswith('??'):
                files.append(line[3:])
            elif len(line) > 2 and line[1] != ' ':
                files.append(line[3:].strip())
        return files[:limit]

    def apply_patch(self, patch_content, reverse=False) -> GitResult:
        if not patch_content: return GitResult(success=False, stderr="No patch content provided.")
        patch_file_path = ''
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.patch', encoding='utf-8') as patch_file:
                patch_file.write(patch_content)
                patch_file_path = patch_file.name
            command = ['git', 'apply', '--cached']
            if reverse: command.append('--reverse')
            command.append(patch_file_path)
            return self._run_command(command)
        except Exception as e:
            return GitResult(success=False, stderr=str(e))
        finally:
            if patch_file_path and os.path.exists(patch_file_path):
                os.unlink(patch_file_path)

    def commit(self, message: str) -> GitResult:
        return self._run_command(['git', 'commit', '-F', '-'], input_data=message)

    def get_project_name(self) -> str:
        return os.path.basename(self.path)

    def get_current_branch(self) -> str:
        result = self._run_command(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
        return result.stdout if result.success else "UNKNOWN"

    def get_branch_status(self) -> tuple[str, str]:
        self._run_command(['git', 'fetch'], timeout=60)
        branch = self.get_current_branch()
        status_result = self._run_command(['git', 'status', '-sb', '--porcelain=v2'])
        if not status_result.success: return f"🌴 On branch {branch}", branch
        status = status_result.stdout
        upstream_match = re.search(r'# branch.upstream (\S+)', status)
        if upstream_match:
            upstream = upstream_match.group(1)
            ahead_behind = re.search(r'# branch.ab \+(\d+) -(\d+)', status)
            if ahead_behind:
                ahead, behind = int(ahead_behind.group(1)), int(ahead_behind.group(2))
                if ahead > 0 and behind > 0: return f"🔀 Diverged from {upstream}", upstream
                elif ahead > 0: return f"🔼 {ahead} commits ahead of {upstream}", upstream
                elif behind > 0: return f"🔽 {behind} commits behind {upstream}", upstream
            return f"✅ Up to date with {upstream}", upstream
        return f"🌴 On branch {branch} (no upstream set)", branch

    def get_changes_summary(self) -> tuple[int, int, int, int]:
        result = self._run_command(['git', 'status', '--porcelain'])
        if not result.success: return 0, 0, 0, 0
        modified, new, deleted, staged = 0, 0, 0, 0
        status_lines = result.stdout.splitlines()
        if not status_lines: return 0, 0, 0, 0
        staged = len([line for line in status_lines if line and line[0] not in (' ', '?')])
        for line in status_lines:
            if not line: continue
            if line.startswith('??'): new += 1
            elif len(line) > 1:
                work_tree_status = line[1]
                if work_tree_status == 'M': modified += 1
                elif work_tree_status == 'D': deleted += 1
        return modified, new, deleted, staged

    def get_recent_history(self, count=7) -> str:
        result = self._run_command(['git', 'log', f'-n{count}', '--oneline', '--pretty=format:%h - %s (%cr)'])
        return result.stdout if result.success else "Could not load history."

    def get_file_diff(self, file_path, staged=False) -> str:
        command = ['git', 'diff', '--no-color'] 
        if staged: command.append('--cached')
        command.extend(['--', file_path])
        result = self._run_command(command)
        return result.stdout if result.success else f"Error getting diff:\n{result.stderr}"

    def get_branches(self) -> tuple[list, list, str]:
        local_res = self._run_command(['git', 'branch'])
        remote_res = self._run_command(['git', 'branch', '-r'])
        local = [b.strip().replace('* ', '') for b in local_res.stdout.splitlines()] if local_res.success else []
        remotes = [b.strip() for b in remote_res.stdout.splitlines() if '->' not in b] if remote_res.success else []
        return local, remotes, self.get_current_branch()

    def get_conflicting_files(self) -> list[str]:
        result = self._run_command(['git', 'diff', '--name-only', '--diff-filter=U'])
        return result.stdout.splitlines() if result.success and result.stdout else []

    def get_stashes(self) -> list[str]:
        result = self._run_command(['git', 'stash', 'list'])
        return result.stdout.splitlines() if result.success and result.stdout else []
        
    def get_git_config(self, key) -> str:
        result = self._run_command(['git', 'config', '--get', key])
        return result.stdout if result.success else ""

    def stage_item(self, item_path) -> GitResult: return self._run_command(['git', 'add', item_path])
    def unstage_item(self, item_path) -> GitResult: return self._run_command(['git', 'reset', 'HEAD', '--', item_path])
    
    def push(self) -> GitResult:
        remotes = self.get_remote_status()
        if 'origin' not in remotes or 'push' not in remotes['origin']:
            logging.error("No 'origin' remote configured for push.")
            return GitResult(success=False, stderr="No 'origin' remote configured for push or remote URL is missing.")
        
        current_branch = self.get_current_branch()
        if current_branch == "UNKNOWN":
            logging.error("Could not determine the current branch.")
            return GitResult(success=False, stderr="Could not determine the current branch.")

        check_upstream_cmd = ['git', 'rev-parse', '--abbrev-ref', f'{current_branch}@{{u}}']
        upstream_res = self._run_command(check_upstream_cmd)
        
        push_command = ['git', 'push']
        if not upstream_res.success:
            logging.info(f"No upstream for branch '{current_branch}'. Setting upstream to 'origin/{current_branch}' on first push.")
            push_command.extend(['--set-upstream', 'origin', current_branch])
        else:
            logging.info(f"Upstream branch found for '{current_branch}'. Performing a regular push.")

        push_res = self._run_command(push_command, timeout=120)
        logging.info(f"Push result: success={push_res.success}, stdout='{push_res.stdout}', stderr='{push_res.stderr}'")
        return push_res

    def checkout_branch(self, branch_name) -> GitResult: return self._run_command(['git', 'checkout', branch_name])
    def merge_branch(self, branch_to_merge) -> GitResult: return self._run_command(['git', 'merge', branch_to_merge])
    def pull(self) -> GitResult: return self._run_command(['git', 'pull'], timeout=120)
    def abort_merge(self) -> GitResult: return self._run_command(['git', 'merge', '--abort'])
    def create_stash(self, message) -> GitResult: return self._run_command(['git', 'stash', 'push', '-m', message])
    def apply_stash(self, stash_ref) -> GitResult: return self._run_command(['git', 'stash', 'pop', stash_ref.split(':')[0]])
    def drop_stash(self, stash_ref) -> GitResult: return self._run_command(['git', 'stash', 'drop', stash_ref.split(':')[0]])
    def set_git_config(self, key, value) -> GitResult: return self._run_command(['git', 'config', '--local', key, value])