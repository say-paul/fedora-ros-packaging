import os
import shutil
import requests
import subprocess
import yaml
import argparse
from tempfile import mkdtemp
from concurrent.futures import ThreadPoolExecutor

def get_default_branch(owner, repo):
    """Fetch the default branch of a repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get("default_branch", "main")
    else:
        print(f"Error fetching default branch: {response.status_code}")
        return "main"  # Fallback to "main"

def fetch_tree_with_git(repo_url, branch=None, temp_dir=None):
    """Clone the repository and fetch the tree structure."""
    # Extract owner and repo from URL
    parts = repo_url.rstrip('.git').split('/')
    owner, repo = parts[-2], parts[-1]

    # Get default branch if not provided
    if not branch:
        branch = get_default_branch(owner, repo)

    # Clone the repository metadata to the temporary directory
    repo_download_path = os.path.join(temp_dir, f"{owner}-{repo}-{branch}-bare")
    subprocess.run(["git", "clone", "--bare", repo_url, repo_download_path], check=True)

    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", branch],
        cwd=repo_download_path,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None, None

    # Parse the tree structure
    files = result.stdout.splitlines()
    tree = {}
    for file in files:
        parts = file.split("/")
        current = tree
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = "file"
    return tree, branch

def find_all_files_in_tree(tree, filename, path=""):
    """Recursively search for all instances of a file in the tree structure."""
    found_files = []
    for key, value in tree.items():
        current_path = f"{path}/{key}" if path else key
        if key == filename:
            folder_name = path.split("/")[-1] if "/" in path else path
            found_files.append((folder_name, current_path))
        elif isinstance(value, dict):  # It's a folder
            found_files.extend(find_all_files_in_tree(value, filename, current_path))
    return found_files

def create_raw_url(owner, repo, branch, file_path):
    """Construct the raw.githubusercontent.com URL for a file."""
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"
    return raw_url

def get_package_dependencies(repo_url, branch, temp_dir, filename_to_find="package.xml"):
    """Fetch package dependencies and construct raw URLs."""
    # Fetch tree and branch
    tree_structure, branch = fetch_tree_with_git(repo_url, branch, temp_dir)

    # Extract owner and repo
    parts = repo_url.rstrip('.git').split('/')
    owner, repo = parts[-2], parts[-1]

    results = {}

    # Find all instances of the file and construct URLs
    if tree_structure:
        found_files = find_all_files_in_tree(tree_structure, filename_to_find)
        if found_files:
            for folder_name, file_path in found_files:
                raw_url = create_raw_url(owner, repo, branch, file_path)
                if not folder_name:
                    folder_name = repo
                results[folder_name] = raw_url
    else:
        print(f"Failed to fetch the repository structure: {repo_url}")

    return results

def parse_and_validate_yaml(distro_yaml_path, output_file, max_threads=15):
    """Parse the distro.yaml, validate repositories, and store results."""
    # Delete the output file if it exists
    if os.path.exists(output_file):
        os.remove(output_file)

    with open(distro_yaml_path, "r") as yaml_file:
        distro_data = yaml.safe_load(yaml_file)

    # Temporary directory for bare repositories
    temp_dir = mkdtemp()

    reconciliation_report = {"total": 0, "matched": 0, "mismatched": 0, "unmatched": 0}

    def process_repo(repo_name, repo_data):
        nonlocal reconciliation_report
        key_value_results = {}

        repo_url = repo_data.get("url")
        if not repo_url:
            reconciliation_report["unmatched"] += 1
            return

        branch = repo_data.get("version", "main")

        dependencies = get_package_dependencies(repo_url, branch, temp_dir)
        for folder_name, raw_url in dependencies.items():
            if folder_name in repo_data.get("packages", []):
                key_value_results[folder_name] = raw_url
                reconciliation_report["matched"] += 1
            else:
                reconciliation_report["mismatched"] += 1

        # Update reconciliation totals
        reconciliation_report["total"] += len(repo_data.get("packages", []))

        # Incrementally save results to the output file
        with open(output_file, "a") as result_file:
            for key, value in key_value_results.items():
                result_file.write(f"{key} => {value}\n")

    try:
        with ThreadPoolExecutor(max_threads) as executor:
            for repo_name, repo_data in distro_data.items():
                executor.submit(process_repo, repo_name, repo_data)
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir)

    # Print reconciliation report
    print("\nReconciliation Report:")
    print(f"Total Packages Declared: {reconciliation_report['total']}")
    print(f"Matched Packages: {reconciliation_report['matched']}")
    print(f"Mismatched Packages: {reconciliation_report['mismatched']}")
    print(f"Unmatched Repositories: {reconciliation_report['unmatched']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse distro.yaml and validate package dependencies.")
    parser.add_argument("pkglist", type=str, help="Path to the distro.yaml file.")
    parser.add_argument("output", type=str, help="Path to the output file.")
    parser.add_argument("--max-threads", type=int, default=15, help="Maximum number of concurrent threads (default: 15).")

    args = parser.parse_args()

    parse_and_validate_yaml(args.pkglist, args.output, args.max_threads)
