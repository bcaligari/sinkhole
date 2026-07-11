#!/usr/bin/env python3
import argparse
import ipaddress
import sys

def main():
    parser = argparse.ArgumentParser(description="Calculate IPv4 subnet details.")
    parser.add_argument('-s', '--subnet', help="CIDR prefix to split the parent network into (numeric or /numeric)")
    parser.add_argument('-x', action='store_true', help="Only display the subnets in CSV pipeline format (requires -s)")
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

    # Parse and validate optional split prefix length (-s)
    split_prefix = None
    if args.subnet:
        s_val = args.subnet
        if s_val.startswith('/'):
            s_val = s_val[1:]
        try:
            split_prefix = int(s_val)
            if not (0 <= split_prefix <= 32):
                raise ValueError()
        except ValueError:
            print(f"Error: Subnet CIDR '{args.subnet}' must be an integer (optionally prefixed with '/') between 0 and 32.", file=sys.stderr)
            sys.exit(1)

        if split_prefix <= prefix_len:
            print(f"Error: Split subnet CIDR /{split_prefix} must be strictly larger than the parent CIDR /{prefix_len}.", file=sys.stderr)
            sys.exit(1)

    # Enforce constraint: -x requires -s
    if args.x and not args.subnet:
        print("Error: Option -x requires option -s/--subnet to be specified.", file=sys.stderr)
        sys.exit(2)

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
    if split_prefix is not None:
        subnets = list(network.subnets(new_prefix=split_prefix))

        if args.x:
            # Output only in CSV format for pipelines
            # format: network_id,networkid/cidr,network mask,broadcast,first_ip,last_ip
            for subnet in subnets:
                s_net = str(subnet.network_address)
                s_cidr = f"{s_net}/{subnet.prefixlen}"
                s_mask = str(subnet.netmask)
                s_broad = str(subnet.broadcast_address)
                s_prefix = subnet.prefixlen

                if s_prefix == 32:
                    s_first = s_net
                    s_last = s_net
                elif s_prefix == 31:
                    s_first = s_net
                    s_last = s_broad
                else:
                    s_first = str(subnet.network_address + 1)
                    s_last = str(subnet.broadcast_address - 1)

                print(f"{s_net},{s_cidr},{s_mask},{s_broad},{s_first},{s_last}")
        else:
            # Human-readable side-by-side details
            num_subnets = 1 << (split_prefix - prefix_len)

            # Get one of the subnets to find its netmask and addressable host count
            sample_subnet = subnets[0]
            sub_netmask = sample_subnet.netmask

            if split_prefix == 32:
                sub_addressable = 1
            elif split_prefix == 31:
                sub_addressable = 2
            else:
                sub_addressable = sample_subnet.num_addresses - 2

            left_lines = [
                f"Network ID: {net_addr}",
                f"Subnet Mask: {netmask}",
                f"CIDR: /{prefix_len}",
                f"Broadcast: {broad_addr}",
                f"Addressable IPs: {addressable_ips}",
                f"First IP: {first_ip}",
                f"Last IP: {last_ip}"
            ]

            right_lines = [
                f"Subnets: {num_subnets}",
                f"Subnet Mask: {sub_netmask}",
                f"CIDR: /{split_prefix}",
                "",
                f"Addressable IPs: {sub_addressable}",
                "",
                ""
            ]

            # Pad left-hand side lines dynamically to align columns
            max_left_len = max(len(line) for line in left_lines)

            for left, right in zip(left_lines, right_lines):
                padded_left = left.ljust(max_left_len)
                if right:
                    print(f"{padded_left} | {right}")
                else:
                    print(f"{padded_left} |")

            print()

            # Table header columns
            col0_header = "subnet"
            col1_header = "net id"
            col2_header = "first"
            col3_header = "last"

            # Determine column widths
            max_idx_len = len(col0_header)
            max_net_len = len(col1_header)
            max_first_len = len(col2_header)
            max_last_len = len(col3_header)

            rows = []
            for idx, subnet in enumerate(subnets):
                s_net = str(subnet.network_address)
                s_broad = subnet.broadcast_address
                s_prefix = subnet.prefixlen

                if s_prefix == 32:
                    s_first = str(s_net)
                    s_last = str(s_net)
                elif s_prefix == 31:
                    s_first = str(s_net)
                    s_last = str(s_broad)
                else:
                    s_first = str(subnet.network_address + 1)
                    s_last = str(subnet.broadcast_address - 1)

                idx_str = str(idx)
                max_idx_len = max(max_idx_len, len(idx_str))
                max_net_len = max(max_net_len, len(s_net))
                max_first_len = max(max_first_len, len(s_first))
                max_last_len = max(max_last_len, len(s_last))

                rows.append((idx_str, s_net, s_first, s_last))

            # Truncate if total subnets > 8: show first 2 and last 2 separated by "..."
            truncate_table = len(subnets) > 8

            # Print Table
            print(f"{col0_header.ljust(max_idx_len)} | {col1_header.ljust(max_net_len)} | {col2_header.ljust(max_first_len)} | {col3_header.ljust(max_last_len)}")
            if truncate_table:
                for row in rows[:2]:
                    print(f"{row[0].ljust(max_idx_len)} | {row[1].ljust(max_net_len)} | {row[2].ljust(max_first_len)} | {row[3].ljust(max_last_len)}")
                print("...")
                for row in rows[-2:]:
                    print(f"{row[0].ljust(max_idx_len)} | {row[1].ljust(max_net_len)} | {row[2].ljust(max_first_len)} | {row[3].ljust(max_last_len)}")
            else:
                for row in rows:
                    print(f"{row[0].ljust(max_idx_len)} | {row[1].ljust(max_net_len)} | {row[2].ljust(max_first_len)} | {row[3].ljust(max_last_len)}")

    else:
        # Standard vertical output
        print(f"Network ID: {net_addr}")
        print(f"Subnet Mask: {netmask}")
        print(f"CIDR: /{prefix_len}")
        print(f"Broadcast: {broad_addr}")
        print(f"Addressable IPs: {addressable_ips}")
        print(f"First IP: {first_ip}")
        print(f"Last IP: {last_ip}")

if __name__ == '__main__':
    main()
