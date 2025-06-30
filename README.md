🚀 GitRocket - A Modern Git GUI Client
GitRocket is a powerful, user-friendly Git GUI client built with Flet and Python, designed to streamline your Git workflow. With an intuitive interface, AI-powered commit message suggestions, and robust Git operations, GitRocket empowers developers to manage repositories efficiently and effectively. Whether you're staging changes, resolving merge conflicts, or pushing to remotes, GitRocket makes version control a breeze.

✨ Features

Interactive Diff View 🖥️: Visualize and selectively stage or unstage changes with a detailed, color-coded diff viewer.
AI-Powered Commit Messages 🤖: Leverage Google's Gemini API to generate conventional commit messages based on your changes.
Branch Management 🌳: Easily switch, merge, and manage local and remote branches with a clean interface.
Merge Conflict Resolution 🚨: Detect and resolve merge conflicts with guided steps and clear file listings.
Stash Management 📦: Create, apply, and delete stashes to manage your working directory seamlessly.
Repository Insights 📊: View branch status, recent commit history, and change summaries at a glance.
Cross-Platform 🌐: Built with Flet, GitRocket runs on Windows, macOS, and Linux.


🛠️ Installation
Prerequisites

Python 3.8+
Git installed and available in your system PATH
A Google Gemini API key (optional, for AI-powered commit messages)

Steps

Clone the Repository
git clone https://github.com/your-username/gitrocket.git
cd gitrocket


Install Dependencies
pip install -r requirements.txt


Set Up EnvironmentCreate a .env file in the project root and add your Gemini API key:
GEMINI_API_KEY=your-api-key-here


Run the Application
python main.py




📖 Usage

Launch GitRocket 🚀Run python main.py to start the application. The welcome screen will prompt you to select a Git repository folder.

Select a Repository 📂Choose a valid Git repository to load. GitRocket will validate the repository and check for Git configuration (user.name and user.email).

Dashboard Overview 🖼️The dashboard displays:

Repository name and path
Branch status (ahead/behind upstream)
Change summary (modified, new, deleted, staged files)
Recent commit history
Stash tray for managing stashed changes


Staging Changes 📋Navigate to the "Launchpad" to review unstaged and staged changes. Use the interactive diff view to stage/unstage specific hunks or entire files.

Committing ✍️Use the Commit Composer to craft conventional commit messages. Optionally, generate AI-suggested messages based on staged changes.

Pushing to Remote 🚀After committing, GitRocket automatically pushes changes to the remote repository, displaying a success or error message.

Branch Management 🌿View and manage local/remote branches, checkout branches, or merge branches into the current one.

Merge Conflict Handling ⚠️If a merge conflict occurs, GitRocket lists conflicting files and guides you through resolution and staging.



🗂️ Project Structure
gitrocket/
├── git_ops.py          # Core Git operations and repository management
├── ui_components.py    # UI components for diff view and commit composer
├── main.py             # Main application entry point
├── requirements.txt    # Project dependencies
├── .env                # Environment variables (e.g., GEMINI_API_KEY)
└── gitrocket.log       # Application logs


🔧 Configuration

Git Configuration: Ensure user.name and user.email are set in your Git repository. GitRocket prompts for configuration if these are missing.
AI Features: A valid GEMINI_API_KEY in the .env file is required for AI-powered commit message suggestions.


📜 Logging
GitRocket logs all operations and errors to gitrocket.log for debugging and auditing purposes. Check this file if you encounter issues.

🤝 Contributing
Contributions are welcome! To contribute:

Fork the repository.
Create a feature branch (git checkout -b feature/your-feature).
Commit your changes (git commit -m "feat: add your feature").
Push to the branch (git push origin feature/your-feature).
Open a Pull Request.

Please ensure your code follows the project's coding style and includes appropriate tests.

📄 License
This project is licensed under the MIT License. See the LICENSE file for details.

🙏 Acknowledgments

Built with Flet for cross-platform UI.
Powered by Google Gemini API for AI-driven commit suggestions.
Inspired by the need for a simple, modern Git GUI.


Happy Coding with GitRocket! 🚀
