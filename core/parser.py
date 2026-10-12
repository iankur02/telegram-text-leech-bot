import os
import re
from typing import List, Dict, Optional, Tuple

class TextParser:
    URL_REGEX = re.compile(r'https?://[^\s]+', re.IGNORECASE)

    @classmethod
    def sanitize_filename(cls, title: str, max_length: int = 120) -> str:
        name = re.sub(r'[\\/]+', ' - ', title)
        name = re.sub(r'[\":*?|<>]+', '', name)
        name = re.sub(r'\s+', ' ', name)
        name = re.sub(r'-\s*-', '-', name)
        name = name.strip(' .-_')
        if len(name) > max_length:
            name = name[:max_length].rstrip(' .-_')
        return name or "video"

    @classmethod
    def parse_line(cls, line: str) -> Optional[Tuple[str, str]]:
        line = line.strip()
        if not line:
            return None

        match = cls.URL_REGEX.search(line)
        if not match:
            return None

        url = match.group(0).strip()
        title_part = line[:match.start()].strip()
        title_part = re.sub(r'[\s:\-|]+$', '', title_part).strip()

        if not title_part:
            path_part = url.split('?')[0].rstrip('/')
            base = os.path.basename(path_part)
            title_part = base if base else "Untitled Video"

        return title_part, url

    @classmethod
    def parse_file(
        cls, 
        file_path_or_content: str, 
        start_index: int = 1, 
        end_index: Optional[int] = None
    ) -> List[Dict]:
        if os.path.isfile(file_path_or_content):
            with open(file_path_or_content, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        else:
            lines = file_path_or_content.splitlines()

        items = []
        counter = 1

        for raw_line in lines:
            parsed = cls.parse_line(raw_line)
            if not parsed:
                continue

            title, url = parsed
            display_idx = f"{counter:03d}"
            formatted_title = f"{display_idx}) {title}"
            safe_name = cls.sanitize_filename(formatted_title)

            items.append({
                "index": counter,
                "display_index": display_idx,
                "raw_title": title,
                "title": formatted_title,
                "safe_filename": safe_name,
                "url": url
            })
            counter += 1

        filtered_items = []
        for item in items:
            idx = item["index"]
            if idx < start_index:
                continue
            if end_index is not None and idx > end_index:
                continue
            filtered_items.append(item)

        return filtered_items
