# Advanced Diff Viewer Editor

This is a text diff viewer component built with Python and PySide6. It provides a side-by-side comparison of two text files with capabilities inspired by modern IDEs and code editors like VS Code and PyCharm.

The component is designed to be easily integrated into larger applications, for instance, to visualize changes suggested by an AI code assistant, allowing a user to review and manually edit the results.

![diff of project commit](/static/preview_self.png)

Turn on da sound! 🎧🗣🔥🎶

https://github.com/user-attachments/assets/9b93e374-a59f-4291-b605-8b2a23d3f3fa

---

## Features

This component implements a wide range of features required for a professional diffing tool:

*   **Beautiful and Clear Presentation**: A modern, dark-themed UI provides a pleasant and readable experience.
*   **Syntax Highlighting**: Uses the powerful `pygments` library to automatically detect the language from the filename and apply syntax highlighting.
*   **Accurate Line Numbers**: Custom-drawn line number bars correctly display the original line numbers, even when parts of the text are collapsed.
*   **Detailed Diff Highlighting**: Clearly marks inserted (`+`) and deleted (`-`) lines with distinct background colors. The highlighting is granular, showing character-level changes within modified lines.
*   **Intelligent Code Folding**: Long sections of unchanged code are automatically collapsed to save space and focus the user's attention on the differences. These sections can be expanded with a single click.
*   **Live Editing**: The "new" version of the text can be edited directly in the viewer. The diff highlighting updates automatically and efficiently as you type.
*   **High Performance & Responsive UI**:
    *   Diff calculations are debounced (run after a short delay) to keep the UI fluid and responsive during rapid typing.
    *   It uses the highly optimized `fast-diff-match-patch` library for near-instant diff results.
    *   Custom drawing logic for line numbers and highlights is optimized to prevent lag.
*   **Command-Line Interface**: Can be run as a standalone tool, accepting two file paths as arguments for comparison.

## Installation

To run this project, you need Python 3 and the following libraries.

1.  Clone the repository:
    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```

2.  Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

You can run the application in two ways:

1.  **With built-in example texts**:
    ```bash
    python main.py
    ```

2.  **Comparing two files from your disk**:
    ```bash
    python main.py path/to/old_file.py path/to/new_file.py
    ```


## Could Be Improved

*   [ ] Implement a mechanism to re-collapse expanded sections.
*   [ ] Run diff calculations in a separate thread (`QThread`) for extremely large files to guarantee the UI never hitches.
*   [ ] Add visual "spacer" elements between discontinuous diff hunks to improve alignment, similar to GitHub's diff view.
*   [ ] Add a "Reload" or "Reset" button to revert all edits and restore the initial collapsed view.

If you want to commit to this project, then solve one of those and submit a Pull Request!
