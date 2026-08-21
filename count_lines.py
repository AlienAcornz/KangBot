import os


def count_lines_in_python_files(start_dir="."):
    total_lines = 0
    total_files = 0

    print(f"{'File Path':<60} | {'Lines':>8}")
    print("-" * 73)

    # os.walk recursively traverses the directory tree
    for root, dirs, files in os.walk(start_dir):
        # Prune .venv directories in-place so os.walk does not recurse into them
        dirs[:] = [d for d in dirs if d != ".venv"]

        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(
                        file_path, "r", encoding="utf-8", errors="ignore"
                    ) as f:
                        # Count non-empty lines
                        line_count = sum(1 for line in f if line.strip())

                    print(f"{file_path:<60} | {line_count:>8}")
                    total_lines += line_count
                    total_files += 1

                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

    print("-" * 73)
    print(f"Total Python Files: {total_files}")
    print(f"Total Lines of Code: {total_lines}")


if __name__ == "__main__":
    count_lines_in_python_files()