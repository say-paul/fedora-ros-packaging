# fedora-ros-packaging
This is an effort to package ros natively for fedora


## rosdistro_package.py
This creates the distro-wise (rolling,jazzy) package list, package names and source repositories.
Running this will create <disto>_package.yaml
This refers to https://github.com/ros/rosdistro to parse the packages.
For any missing source URLs it reports error, which needs to be manually adjusted for now(TODO)

## package_dependecies.py
This accepts the files created by rosdistro_package.py and does a --bare clone of the repo to get
to match the packages and their relative package.xaml, for found matches, it saves them as key value
