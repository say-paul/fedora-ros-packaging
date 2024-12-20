import os
import requests
import yaml

def distro_dist_search(distro):
    distribution_yaml = f"https://raw.githubusercontent.com/ros/rosdistro/master/{distro}/distribution.yaml"
    
    # Output YAML file
    output_file = f"{distro}_packages.yaml"
    
    # Retrieve the file content from the URL
    response = requests.get(distribution_yaml, allow_redirects=True)
    response.raise_for_status()  # Raise an exception for HTTP errors
    
    # Convert bytes to string
    content = response.content.decode("utf-8")
    
    # Load the YAML
    content = yaml.safe_load(content)
    
    # Get the list of repositories
    repositories = content.get("repositories", {})
    
    # Dictionary to store consolidated package data
    consolidated_data = {}
    
    for package_name, package_info in repositories.items():
        if package_info:
            source_info = package_info.get("source", {})
            release_info = package_info.get("release", {})
            git_url = source_info.get("url")
            if not git_url:
                print(f"Error: git_url is empty for package: {package_name}")
                # continue
                
            # Prepare the package data
            consolidated_data[package_name] = {
                "type": source_info.get("type", "git"),
                "url": git_url,
                "version": source_info.get("version", None),
                "packages": release_info.get("packages", [package_name]),
                "package_version": release_info.get("version", None),
            }
    
    # Save the consolidated data to a YAML file
    with open(output_file, "w") as yaml_file:
        yaml.dump(consolidated_data, yaml_file, default_flow_style=False)
    print(f"Consolidated YAML saved to {output_file}")

DISTROS = ["rolling","jazzy"]
for distro in DISTROS:
 print(f"Scraping from {distro}")
 distro_dist_search(distro)