#!/usr/bin/env python3
import argparse
import ipaddress
import sys

def main():
    parser = argparse.ArgumentParser(description="Calculate IPv4 subnet details.")
    parser.add_argument('subnet_cidr', help="Subnet in CIDR format (a.b.c.d/e)")
    args = parser.parse_args()

    cidr_str = args.subnet_cidr

    # Basic format pre-validation
    if '/' not in cidr_str or cidr_str.count('/') != 1:
        print("Error: Input must be in the format 'a.b.c.d/e' containing exactly one '/' separator.", file=sys.stderr)
        sys.exit(1)

    ip_part, prefix_part = cidr_str.split('/')

    # Validate CIDR prefix length boundary
    try:
        prefix = int(prefix_part)
        if not (0 <= prefix <= 32):
            raise ValueError()
    except ValueError:
        print(f"Error: CIDR prefix size '{prefix_part}' must be an integer between 0 and 32.", file=sys.stderr)
        sys.exit(1)

    # Validate IP address octets format
    octets = ip_part.split('.')
    if len(octets) != 4:
        print(f"Error: IP address part '{ip_part}' must contain exactly four octets separated by dots.", file=sys.stderr)
        sys.exit(1)

    for o in octets:
        try:
            val = int(o)
            if not (0 <= val <= 255):
                raise ValueError()
        except ValueError:
            print(f"Error: IP address octet '{o}' must be an integer between 0 and 255.", file=sys.stderr)
            sys.exit(1)

    # Calculate using built-in standard library ipaddress module (uses exact integer bitwise operations)
    try:
        # IPv4Interface tolerates host bits set (e.g. 192.168.1.100/24), which is desired
        interface = ipaddress.IPv4Interface(cidr_str)
        network = interface.network
    except Exception as e:
        print(f"Error: Invalid IPv4 CIDR address: {e}", file=sys.stderr)
        sys.exit(1)

    net_addr = network.network_address
    broad_addr = network.broadcast_address
    prefix_len = network.prefixlen
    netmask = network.netmask

    # Calculate Addressable IP count, First IP, and Last IP based on subnet size
    if prefix_len == 32:
        addressable_ips = 1
        first_ip = net_addr
        last_ip = net_addr
    elif prefix_len == 31:
        addressable_ips = 2
        first_ip = net_addr
        last_ip = broad_addr
    else:
        addressable_ips = network.num_addresses - 2
        first_ip = net_addr + 1
        last_ip = broad_addr - 1

    # Output details
    print(f"Network ID: {net_addr}")
    print(f"Subnet Mask: {netmask}")
    print(f"CIDR: /{prefix_len}")
    print(f"Broadcast: {broad_addr}")
    print(f"Addressable IPs: {addressable_ips}")
    print(f"First IP: {first_ip}")
    print(f"Last IP: {last_ip}")

if __name__ == '__main__':
    main()
