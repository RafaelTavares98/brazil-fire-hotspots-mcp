"""Check every link and anchor in the project's markdown.

The invoice pipeline validated its own docs the same way. A link that
points nowhere is a promise the reader cannot keep.

Usage: python check_links.py
Exit code 1 when anything is broken.
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

LINK = re.compile(r'\[[^\]]*\]\(([^)]+)\)')


def slug(heading):
    text = heading.strip().lower()
    text = re.sub(r'[^a-z0-9 _\-]', '', text)
    text = re.sub(r'[ \-]+', '-', text)
    return text.strip('-')


def anchors_of(path):
    found = set()
    for line in path.read_text(encoding='utf-8').splitlines():
        match = re.match(r'^#{1,6}\s+(.*)', line)
        if match:
            found.add(slug(match.group(1)))
    return found


def main():
    broken = []
    files = sorted(HERE.glob('**/*.md'))
    for file in files:
        if '.git' in file.parts:
            continue
        for line_number, line in enumerate(
                file.read_text(encoding='utf-8').splitlines(), start=1):
            for target in LINK.findall(line):
                if target.startswith(('http://', 'https://')):
                    continue
                path_part, _, anchor = target.partition('#')
                if not path_part:
                    target_file = file
                else:
                    target_file = (file.parent / path_part).resolve()
                if not target_file.exists():
                    broken.append(
                        f'{file}:{line_number} missing file {target}')
                    continue
                if anchor:
                    if target_file.suffix != '.md':
                        continue
                    if anchor not in anchors_of(target_file):
                        broken.append(
                            f'{file}:{line_number} missing anchor '
                            f'#{anchor} in {target}')
    for message in broken:
        print(message)
    if broken:
        print(f'{len(broken)} broken links')
        sys.exit(1)
    print(f'{len(files)} files, every link and anchor checked, none broken')


if __name__ == '__main__':
    main()
