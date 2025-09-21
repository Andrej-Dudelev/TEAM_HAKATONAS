import os

# --- Configuration ---
# The directory to start scanning from. '.' means the current directory.
ROOT_DIRECTORY = "."

# The name of the file where the output will be saved.
OUTPUT_FILE = "project_context.txt"

# Directories to completely ignore.
# Added a few common ones like .git, __pycache__, etc. for convenience.
IGNORE_DIRECTORIES = {
    "venv",
    ".venv",
    ".git",
    "__pycache__",
    ".vscode",
    "node_modules",
    "static",  # <<< Added this line to ignore the static folder
}

# Specific files to ignore.
IGNORE_FILES = {
    ".env",
    ".gitignore",
    OUTPUT_FILE,  # Don't include the output file in itself
}

# File extensions to ignore (e.g., compiled files, images, logs).
IGNORE_EXTENSIONS = {
    ".pyc",
    ".log",
    ".lock",
    ".DS_Store",
    ".sqlite3",
    ".db",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".webp",
}
# ---------------------


def extract_project_data(root_dir, output_file):
    """
    Extracts directory structure, filenames, and file contents to a single text file.

    Args:
        root_dir (str): The path to the root directory of the project.
        output_file (str): The name of the file to save the extracted data to.
    """
    print(f"🚀 Starting extraction from '{os.path.abspath(root_dir)}'...")

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"Project Context for: {os.path.abspath(root_dir)}\n")
            f.write("=" * 80 + "\n\n")

            # os.walk is a generator that recursively walks the directory tree.
            # topdown=True allows us to modify the list of directories to visit.
            for dirpath, dirnames, filenames in os.walk(root_dir, topdown=True):
                # Modify dirnames in-place to prevent os.walk from descending
                # into ignored directories. This is much more efficient.
                dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRECTORIES]

                # --- Write current directory path ---
                # We normalize the path for consistent representation.
                relative_dirpath = os.path.relpath(dirpath, root_dir)
                if relative_dirpath != ".": # Don't print the root dir name twice
                    f.write(f"--- DIRECTORY: {relative_dirpath} ---\n\n")

                for filename in sorted(filenames):
                    # Check if the file or its extension should be ignored
                    if filename in IGNORE_FILES:
                        continue
                    if os.path.splitext(filename)[1] in IGNORE_EXTENSIONS:
                        continue

                    file_path = os.path.join(dirpath, filename)
                    relative_file_path = os.path.relpath(file_path, root_dir)

                    # --- Write file header and content ---
                    f.write(f"--- FILE: {relative_file_path} ---\n")
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as content_file:
                            contents = content_file.read()
                            f.write(contents)
                            f.write("\n\n")
                    except Exception as e:
                        f.write(f"*** Could not read file: {e} ***\n\n")

    except IOError as e:
        print(f"❌ Error writing to file {output_file}: {e}")
        return
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        return

    print(f"✅ Success! Project data extracted to '{output_file}'.")


if __name__ == "__main__":
    extract_project_data(ROOT_DIRECTORY, OUTPUT_FILE)