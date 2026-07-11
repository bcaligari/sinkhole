#!/usr/bin/env python3
import argparse
import datetime
import html
import os
import re
import sys
import xml.etree.ElementTree as ET

def semver_sort_key(version_str):
    """
    Split a version string into a tuple of components for semantic sorting.
    If a component is purely numeric, it's compared numerically.
    If it's a mix of numeric and alpha, it's compared alphanumerically as a string.
    """
    if not version_str:
        return ()
    parts = re.split(r'[\.\-_+]', version_str)
    key = []
    for part in parts:
        if not part:
            continue
        if part.isdigit():
            key.append((0, int(part)))
        else:
            key.append((1, part.lower()))
    return tuple(key)

def find_child(elem, tag_name):
    """Find the first direct child element with the matching local tag name (ignoring namespace)."""
    for child in elem:
        if child.tag.split('}')[-1] == tag_name:
            return child
    return None

def find_child_text(elem, tag_name):
    """Get the text of the first direct child with the matching local tag name."""
    child = find_child(elem, tag_name)
    return child.text if child is not None else None

def find_all_children(elem, tag_name):
    """Find all direct child elements with the matching local tag name."""
    res = []
    for child in elem:
        if child.tag.split('}')[-1] == tag_name:
            res.append(child)
    return res

def format_issued_date(date_str):
    """Format a Unix timestamp to a human-readable date, or return as-is if parsing fails."""
    try:
        timestamp = int(date_str)
        dt = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return date_str

def open_compressed_or_plain(filepath, mode='rb'):
    """Open a file, decompressing it on-the-fly based on its extension."""
    ext = filepath.lower().split('.')[-1]
    if ext == 'gz':
        import gzip
        return gzip.open(filepath, mode)
    elif ext == 'bz2':
        import bz2
        return bz2.open(filepath, mode)
    elif ext in ('xz', 'lzma'):
        import lzma
        return lzma.open(filepath, mode)
    elif ext in ('zst', 'zstd'):
        try:
            from compression import zstd
            return zstd.open(filepath, mode)
        except ImportError:
            raise RuntimeError(f"Zstandard decompression for '{filepath}' requires Python 3.14+ or 'compression.zstd' module.")
    else:
        return open(filepath, mode)

def is_updateinfo_file(filename):
    """Check if the filename matches updateinfo xml patterns (raw or compressed)."""
    fn = filename.lower()
    valid_suffixes = (
        'updateinfo.xml',
        'updateinfo.xml.gz',
        'updateinfo.xml.bz2',
        'updateinfo.xml.xz',
        'updateinfo.xml.zst'
    )
    return any(fn.endswith(suffix) for suffix in valid_suffixes)

def main():
    parser = argparse.ArgumentParser(description="Query updateinfo.xml for package updates.")
    parser.add_argument('-p', '--package-name', help="Package name")
    parser.add_argument('-v', '--version', help="Package version (optional)")
    parser.add_argument('-r', '--release', help="Package release (optional, requires -v)")
    parser.add_argument('-d', '--details', action='store_true', help="Output detailed HTML information for each patch")
    parser.add_argument('-l', '--list-packages', action='store_true', help="List all RPM filenames in each patch section (requires -d)")
    parser.add_argument('-s', '--summary', action='store_true', help="Output summary statistics of all patches (mutually exclusive with package filters/details)")
    parser.add_argument('update_info_xml', help="Path to the updateinfo XML file or directory")

    args = parser.parse_args()

    # Enforce mutual exclusivity of -s with all other options (except positional)
    if args.summary:
        if args.package_name or args.version or args.release or args.details or args.list_packages:
            parser.error("argument -s/--summary: not allowed with package filtering (-p, -v, -r) or details (-d, -l) options")
    else:
        # If -s is not chosen, -p is mandatory
        if not args.package_name:
            parser.error("the following arguments are required: -p/--package-name")

    # Enforce constraint: -r is optional but only if -v is set
    if args.release and not args.version:
        parser.error("argument -r/--release: requires -v/--version to be set")

    # Enforce constraint: -l is optional but only if -d is set
    if args.list_packages and not args.details:
        parser.error("argument -l/--list-packages: requires -d/--details to be set")

    # Collect files to parse
    files_to_parse = []
    if os.path.isdir(args.update_info_xml):
        for root_dir, _, filenames in os.walk(args.update_info_xml):
            for filename in filenames:
                if is_updateinfo_file(filename):
                    files_to_parse.append(os.path.join(root_dir, filename))
    elif os.path.isfile(args.update_info_xml):
        files_to_parse.append(args.update_info_xml)
    else:
        print(f"Error: Path not found or invalid: {args.update_info_xml}", file=sys.stderr)
        sys.exit(1)

    if not files_to_parse:
        print(f"No updateinfo files found in: {args.update_info_xml}")
        return

    matching_updates = {}

    for filepath in files_to_parse:
        try:
            with open_compressed_or_plain(filepath, 'rb') as f:
                tree = ET.parse(f)
                root = tree.getroot()
        except Exception as e:
            print(f"Error parsing XML file '{filepath}': {e}", file=sys.stderr)
            sys.exit(1)

        # Find all <update> elements anywhere in the tree
        for update in root.iter():
            if update.tag.split('}')[-1] != 'update':
                continue

            update_id = find_child_text(update, 'id') or 'N/A'
            issued_elem = find_child(update, 'issued')
            issued_date = issued_elem.get('date') if issued_elem is not None else 'N/A'

            if args.summary:
                # In summary mode, we collect all unique updates without package filtering
                if update_id not in matching_updates:
                    matching_updates[update_id] = {
                        'id': update_id,
                        'issued_date': issued_date
                    }
            else:
                # Normal mode: filter by package name
                pkglist_elem = find_child(update, 'pkglist')
                if pkglist_elem is None:
                    continue

                matched_packages = []

                # Packages are inside <collection>/<package> under <pkglist>
                for collection in find_all_children(pkglist_elem, 'collection'):
                    for pkg in find_all_children(collection, 'package'):
                        pkg_name = pkg.get('name')
                        pkg_ver = pkg.get('version')
                        pkg_rel = pkg.get('release')

                        if pkg_name == args.package_name:
                            if args.version is not None and pkg_ver != args.version:
                                continue
                            if args.release is not None and pkg_rel != args.release:
                                continue

                            filename_elem = find_child(pkg, 'filename')
                            filename = filename_elem.text if filename_elem is not None else ''

                            matched_packages.append({
                                'name': pkg_name,
                                'epoch': pkg.get('epoch', '0'),
                                'version': pkg_ver,
                                'release': pkg_rel,
                                'arch': pkg.get('arch', 'N/A'),
                                'src': pkg.get('src', 'N/A'),
                                'filename': filename
                            })

                if matched_packages:
                    title = find_child_text(update, 'title') or 'N/A'
                    severity = find_child_text(update, 'severity') or 'N/A'
                    release = find_child_text(update, 'release') or 'N/A'
                    description = find_child_text(update, 'description') or ''

                    update_from = update.get('from', 'N/A')
                    update_status = update.get('status', 'N/A')
                    update_type = update.get('type', 'N/A')
                    update_version = update.get('version', 'N/A')

                    references = []
                    references_elem = find_child(update, 'references')
                    if references_elem is not None:
                        for ref in find_all_children(references_elem, 'reference'):
                            references.append({
                                'id': ref.get('id', 'N/A'),
                                'title': ref.get('title', 'N/A'),
                                'type': ref.get('type', 'N/A'),
                                'href': ref.get('href', 'N/A')
                            })

                    # Extract all package filenames in this update
                    all_rpm_filenames = []
                    for collection in find_all_children(pkglist_elem, 'collection'):
                        for pkg in find_all_children(collection, 'package'):
                            filename_elem = find_child(pkg, 'filename')
                            if filename_elem is not None and filename_elem.text:
                                all_rpm_filenames.append(filename_elem.text)

                    if update_id in matching_updates:
                        # Merge matching updates across files
                        existing = matching_updates[update_id]
                        seen_pkgs = {(p['name'], p['version'], p['release'], p['arch']) for p in existing['packages']}
                        for p in matched_packages:
                            key = (p['name'], p['version'], p['release'], p['arch'])
                            if key not in seen_pkgs:
                                existing['packages'].append(p)
                                seen_pkgs.add(key)
                        seen_refs = {r['id'] for r in existing['references']}
                        for r in references:
                            if r['id'] not in seen_refs:
                                existing['references'].append(r)
                                seen_refs.add(r['id'])
                        existing_rpms = set(existing['all_rpm_filenames'])
                        for r in all_rpm_filenames:
                            if r not in existing_rpms:
                                existing['all_rpm_filenames'].append(r)
                                existing_rpms.add(r)
                    else:
                        matching_updates[update_id] = {
                            'id': update_id,
                            'title': title,
                            'severity': severity,
                            'release_title': release,
                            'description': description.strip(),
                            'from': update_from,
                            'status': update_status,
                            'type': update_type,
                            'version': update_version,
                            'issued_date': issued_date,
                            'references': references,
                            'packages': matched_packages,
                            'all_rpm_filenames': all_rpm_filenames
                        }

    # Summary output mode
    if args.summary:
        if not matching_updates:
            print("No patches found.")
            return

        # Parse and filter out valid timestamps
        timestamps = []
        for upd in matching_updates.values():
            try:
                ts = int(upd['issued_date'])
                timestamps.append(ts)
            except (ValueError, TypeError):
                continue

        if not timestamps:
            print("Date of first patch: N/A")
            print("Date of last patch:  N/A")
            print(f"Total patch count: {len(matching_updates)}")
            return

        first_patch_ts = min(timestamps)
        last_patch_ts = max(timestamps)

        first_patch_date = format_issued_date(str(first_patch_ts))
        last_patch_date = format_issued_date(str(last_patch_ts))

        print(f"Date of first patch: {first_patch_date}")
        print(f"Date of last patch:  {last_patch_date}")
        print(f"Total patch count: {len(matching_updates)}")
        return

    if not matching_updates:
        filter_str = f"package '{args.package_name}'"
        if args.version:
            filter_str += f", version '{args.version}'"
        if args.release:
            filter_str += f", release '{args.release}'"
        print(f"No updates found matching {filter_str}.")
        return

    # Extract rows for the table and deduplicate them (e.g. across multiple package architectures)
    rows = []
    seen = set()
    for upd in matching_updates.values():
        release_date = format_issued_date(upd['issued_date'])
        patch_id = upd['id']
        for pkg in upd['packages']:
            version = pkg['version']
            release = pkg['release']
            row_key = (release_date, version, release, patch_id)
            if row_key not in seen:
                seen.add(row_key)
                rows.append({
                    'release_date': release_date,
                    'version': version,
                    'release': release,
                    'patch_id': patch_id
                })

    # Sort rows first by version, then by release (semantically)
    rows.sort(key=lambda r: (semver_sort_key(r['version']), semver_sort_key(r['release'])))

    # Render as HTML details if --details is specified
    if args.details:
        print("<!DOCTYPE html>")
        print("<html>")
        print("<head>")
        print("  <meta charset=\"utf-8\">")
        print("  <title>Update Details</title>")
        print("  <style>")
        print("    body { font-family: sans-serif; margin: 20px; line-height: 1.5; }")
        print("    table { font-family: monospace; border-collapse: collapse; width: 100%; margin-bottom: 40px; }")
        print("    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }")
        print("    th { background-color: #f2f2f2; }")
        print("    tr:nth-child(even) { background-color: #f9f9f9; }")
        print("    tr:hover { background-color: #f1f1f1; }")
        print("    pre { white-space: pre-wrap; background-color: #f8f9fa; border: 1px solid #e9ecef; padding: 15px; border-radius: 4px; }")
        print("    code { font-family: monospace; }")
        print("    .patch-block { margin-top: 40px; border-top: 2px solid #333; padding-top: 20px; }")
        print("  </style>")
        print("</head>")
        print("<body id=\"top\">")

        # HTML Table
        print("<table>")
        print("  <thead>")
        print("    <tr>")
        print("      <th>Release Date</th>")
        print("      <th>Version</th>")
        print("      <th>Release</th>")
        print("      <th>Patch ID</th>")
        print("    </tr>")
        print("  </thead>")
        print("  <tbody>")
        for row in rows:
            escaped_date = html.escape(row['release_date'])
            escaped_version = html.escape(row['version'])
            escaped_release = html.escape(row['release'])
            escaped_patch_id = html.escape(row['patch_id'])
            print("    <tr>")
            print(f"      <td>{escaped_date}</td>")
            print(f"      <td>{escaped_version}</td>")
            print(f"      <td>{escaped_release}</td>")
            print(f"      <td><a href=\"#{escaped_patch_id}\">{escaped_patch_id}</a></td>")
            print("    </tr>")
        print("  </tbody>")
        print("</table>")

        # Details Section for each unique patch
        seen_update_ids = set()
        for row in rows:
            upd_id = row['patch_id']
            if upd_id in seen_update_ids:
                continue
            seen_update_ids.add(upd_id)
            upd = matching_updates[upd_id]

            formatted_date = format_issued_date(upd['issued_date'])
            escaped_id = html.escape(upd_id)
            escaped_title = html.escape(upd['title'])
            escaped_type = html.escape(upd['type'])
            escaped_status = html.escape(upd['status'])
            escaped_severity = html.escape(upd['severity'])
            escaped_date_str = html.escape(formatted_date)

            # Get unique version-release combinations for matching packages under this update (sorted semantically)
            pkg_ver_rels_raw = list(set((pkg['version'], pkg['release']) for pkg in upd['packages']))
            pkg_ver_rels_raw.sort(key=lambda item: (semver_sort_key(item[0]), semver_sort_key(item[1])))
            pkg_ver_rels = [f"{version}-{release}" for version, release in pkg_ver_rels_raw]
            ver_rel_suffix = html.escape(", ".join(pkg_ver_rels))

            print(f"<div class=\"patch-block\" id=\"{escaped_id}\">")
            print(f"  <h2>{escaped_id} ({ver_rel_suffix})</h2>")
            print(f"  <ul>")
            print(f"    <li><strong>Title:</strong> {escaped_title}</li>")
            print(f"    <li><strong>Type:</strong> {escaped_type}</li>")
            print(f"    <li><strong>Status:</strong> {escaped_status}</li>")
            print(f"    <li><strong>Severity:</strong> {escaped_severity}</li>")
            print(f"    <li><strong>Issued Date:</strong> {escaped_date_str}</li>")
            print(f"  </ul>")
            print()

            # List all RPM names in monospace format if --list-packages / -l is specified
            if args.list_packages and upd['all_rpm_filenames']:
                print("  <h3>Packages</h3>")
                print("  <ul>")
                for fn in sorted(list(set(upd['all_rpm_filenames']))):
                    escaped_fn = html.escape(fn)
                    print(f"    <li><code>{escaped_fn}</code></li>")
                print("  </ul>")
                print()

            print("  <h3>Description</h3>")
            escaped_description = html.escape(upd['description'])
            print(f"  <pre>{escaped_description}</pre>")
            print("  <p><a href=\"#top\">Back to top</a></p>")
            print("</div>")

        print("</body>")
        print("</html>")
    else:
        # Render as standard terminal ASCII table
        headers = ["Release Date", "Version", "Release", "Patch ID"]
        col_keys = ["release_date", "version", "release", "patch_id"]

        # Calculate column widths
        col_widths = {key: len(header) for key, header in zip(col_keys, headers)}
        for row in rows:
            for key in col_keys:
                col_widths[key] = max(col_widths[key], len(str(row[key])))

        # Print ASCII table
        border_line = "+" + "+".join("-" * (col_widths[key] + 2) for key in col_keys) + "+"
        header_line = "|" + "|".join(f" {headers[i].ljust(col_widths[key])} " for i, key in enumerate(col_keys)) + "|"

        print(border_line)
        print(header_line)
        print(border_line)
        for row in rows:
            row_line = "|" + "|".join(f" {str(row[key]).ljust(col_widths[key])} " for key in col_keys) + "|"
            print(row_line)
        print(border_line)

if __name__ == '__main__':
    main()
