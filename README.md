# fedora-ros-packaging
This is an effort to package ros natively for fedora


## rosdistro_package.py
This create the drisro-wise(rolling,jazzy) package list, packages names abd source repositories.
Running this will create <disto>_package.yaml
This refers to https://github.com/ros/rosdistro to parse the packages.
For any missing source urls it reports error , which needs to be manually adjusted for now(TODO)
