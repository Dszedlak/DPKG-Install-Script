# dpkg-install-script

An APT install alternative.
This is useful for large offline package installations where apt install can be frustrating.
DPKG does not offer any sense of package sorting. If you give dpkg a list of packages to install it will install them in alphabetic order, along with any dependencies.
This script aims to provide a way of sorting these packages and installing them. 

Other similar scripts exist, but this script has been streamlined to be more lightweight and leave less of a footprint. 

In order to use, change script dir to desired directory.
