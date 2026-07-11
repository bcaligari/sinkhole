# sinkhole

Monorepo of miscellaneous tools I cobbled together for my own amusement in my own
time using my own resources such as my own laptop, SBCs, SDRs, coding assistant
subs, ...

## zuip - Zypp UpdateInfo Parser

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
Network ID: 172.16.0.0    | Subnets: 32
Subnet Mask: 255.255.0.0  | Subnet Mask: 255.255.248.0
CIDR: /16                 | CIDR: /21
Broadcast: 172.16.255.255 |
Addressable IPs: 65534    | Addressable IPs: 2046
First IP: 172.16.0.1      |
Last IP: 172.16.255.254   |

subnet | net id       | first        | last          
0      | 172.16.0.0   | 172.16.0.1   | 172.16.7.254  
1      | 172.16.8.0   | 172.16.8.1   | 172.16.15.254 
...
30     | 172.16.240.0 | 172.16.240.1 | 172.16.247.254
31     | 172.16.248.0 | 172.16.248.1 | 172.16.255.254
```