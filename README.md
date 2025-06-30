# GitRocket

![Language](https://img.shields.io/badge/language-Python-blue.svg)
![Framework](https://img.shields.io/badge/framework-Flet-yellowgreen.svg)
![AI Integration](https://img.shields.io/badge/AI-Gemini-orange.svg)
![Status](https://img.shields.io/badge/status-In%20Development-red.svg)

GitRocket is a desktop application built with Python and Flet that provides a graphical interface for common Git operations, focusing on streamlining the staging and commit workflow. It includes features like interactive diff viewing, guided commit message composition, and optional AI-powered commit message suggestions via Google Gemini.

![LLModel Chat Demo](https://raw.githubusercontent.com/LMLK-seal/GitRocket/refs/heads/main/Example.gif)

✨ Features

*   Graphical User Interface for Git (using Flet).
*   Display repository status (current branch, changes summary, recent history).
*   Interactive Staging Area: View unstaged/staged files and their diffs.
*   Hunk-based staging/unstaging directly from the diff view.
*   Guided Commit Message Composer following Conventional Commits style.
*   🤖 AI Suggestion for Commit Messages (requires Google Gemini API key).
*   Perform basic Git operations: Stage, Unstage, Commit, Push, Pull, Checkout, Merge, Stash.
*   Handle Merge Conflicts graphically.
*   Manage Git user configuration per repository.
*   Persist the last opened project path.

📚 Tech Stack

*   **Language:** Python
*   **GUI Framework:** Flet
*   **Git Operations:** `subprocess` module executing standard `git` commands.
*   **AI Integration:** `google-generativeai` library.
*   **Environment Variables:** `python-dotenv`.

🚀 Installation

1.  **Prerequisites:**
    *   Python 3.8 or higher
    *   Git installed and available in your system's PATH.
    *   (Optional for AI features) A Google Cloud project with access to the Gemini API and a generated API key.

2.  **Clone the repository:**
    ```bash
    https://github.com/LMLK-Seal/gitrocket.git
    cd gitrocket
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Setup Environment Variables (Optional for AI):**
    *   Create a file named `.env` in the root directory of the project.
    *   Add your Google Gemini API key:
        ```env
        GEMINI_API_KEY=YOUR_API_KEY_HERE
        ```
    *   Replace `YOUR_API_KEY_HERE` with your actual key.

▶️ Usage

1.  **Run the application:**
    ```bash
    python main.py
    ```

2.  **Select a Repository:**
    *   The application will open to a welcome screen.
    *   Click the "Load Project Folder" button.
    *   Select the root directory of a local Git repository.

3.  **Dashboard:**
    *   After loading a repository, you'll see the dashboard with the current branch status, change summary, stash tray, and recent history.
    *   Click "Review Changes" to go to the staging area.

4.  **Staging Area:**
    *   View unstaged and staged files.
    *   Click on a file name to view its diff below.
    *   In the diff view, you can select specific hunks (sections of changes) using checkboxes and click "Stage Selected" or "Unstage Selected" to move them between areas.
    *   Use the "Stage All" and "Unstage All" buttons for bulk actions.
    *   Once files are staged, click "Compose Commit Message".

5.  **Commit Composer:**
    *   Fill in the commit message details (Type, Scope, Subject, Body, Footer) following the Conventional Commits structure.
    *   (If AI is configured) Click "AI Suggest" to get a suggested commit message based on staged changes.
    *   Click "Commit & Launch" to commit the staged changes and then push to the configured remote.

6.  **Branch Management:**
    *   Access branch management from the dashboard (LAN icon). View local and remote branches, checkout local branches, or merge branches into the current one.

7.  **Settings:**
    *   Access settings from the dashboard.
    *   Configure the `user.name` and `user.email` for the current repository. You can also change the project folder from here.

🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

<div align="center">
  
**If GitRocket helped streamline your workflow, consider giving us a ⭐!**

*Made with 🤖 by developers, for developers*

</div>
