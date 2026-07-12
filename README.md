# sinkhole

Monorepo of miscellaneous tools I cobbled together for my own amusement in my own
time using my own resources such as my own laptop, SBCs, SDRs, coding assistant
subs, ...

## zuip - Zypp UpdateInfo Parser

### Usage
```{text}
usage: zuip.py [-h] [-p PACKAGE_NAME] [-v VERSION] [-r RELEASE] [-d] [-l] [-s]
               update_info_xml

Query updateinfo.xml for package updates.

positional arguments:
  update_info_xml       Path to the updateinfo XML file or directory

options:
  -h, --help            show this help message and exit
  -p, --package-name PACKAGE_NAME
                        Package name
  -v, --version VERSION
                        Package version (optional)
  -r, --release RELEASE
                        Package release (optional, requires -v)
  -d, --details         Output detailed HTML information for each patch
  -l, --list-packages   List all RPM filenames in each patch section (requires
                        -d)
  -s, --summary         Output summary statistics of all patches (mutually
                        exclusive with package filters/details)
```

### Examples
```{bash}
podman run -it --rm \
    --security-opt label=disable \
    -v "$(pwd)":/opt/app \
    -v /var/cache/zypp/raw:/zyppcache \
    -w /opt/app \
    registry.suse.com/bci/python:3.14-micro \
    python3.14 zuip.py -p glibc /zyppcache
```

```{text}
+---------------------+---------+------------+-------------------------+
| Release Date        | Version | Release    | Patch ID                |
+---------------------+---------+------------+-------------------------+
| 2026-07-03 13:19:16 | 2.40    | 160000.6.1 | openSUSE-Leap-16.0-1157 |
| 2026-01-29 17:44:57 | 2.40    | 160000.3.1 | openSUSE-Leap-16.0-218  |
| 2026-04-10 06:36:43 | 2.40    | 160000.4.1 | openSUSE-Leap-16.0-516  |
| 2026-05-18 05:38:10 | 2.40    | 160000.5.1 | openSUSE-Leap-16.0-761  |
+---------------------+---------+------------+-------------------------+
```

## subnetIPv4 - Yet Another IPv4 Subnet Calculator

### Usage
```{text}
usage: subnetIPv4.py [-h] [-s SUBNET] [-x] subnet_cidr

Calculate IPv4 subnet details.

positional arguments:
  subnet_cidr          Subnet in CIDR format (a.b.c.d/e)

options:
  -h, --help           show this help message and exit
  -s, --subnet SUBNET  CIDR prefix to split the parent network into (numeric
                       or /numeric)
  -x                   Only display the subnets in CSV pipeline format
                       (requires -s)
```

### Examples
```{text}
$ subnetIPv4.py 172.16.0.0/16
Network ID: 172.16.0.0
Subnet Mask: 255.255.0.0
CIDR: /16
Broadcast: 172.16.255.255
Addressable IPs: 65534
First IP: 172.16.0.1
Last IP: 172.16.255.254
```

```{text}
$ subnetIPv4.py 172.16.0.0/16 -s /21
Primary network           | Subnets
------------------------- | --------------------------
Network ID: 172.16.0.0    | Subnets: 32
Subnet Mask: 255.255.0.0  | Subnet Mask: 255.255.248.0
CIDR: /16                 | CIDR: /21
Broadcast: 172.16.255.255 |
Addressable IPs: 65534    | Addressable IPs: 2046
First IP: 172.16.0.1      | First subnet: 172.16.0.0
Last IP: 172.16.255.254   | Last subnet: 172.16.248.0

subnet | net id       | first ip     | last ip       
------ | ------------ | ------------ | --------------
0      | 172.16.0.0   | 172.16.0.1   | 172.16.7.254  
1      | 172.16.8.0   | 172.16.8.1   | 172.16.15.254 
...
30     | 172.16.240.0 | 172.16.240.1 | 172.16.247.254
31     | 172.16.248.0 | 172.16.248.1 | 172.16.255.254
```