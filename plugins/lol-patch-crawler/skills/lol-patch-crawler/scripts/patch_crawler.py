#!/usr/bin/env python3
"""
LoL Patch Notes Crawler
리그 오브 레전드 패치노트 HTML을 크롤링합니다. 기본은 파일 저장,
`--stdout` 옵션을 주면 파일을 만들지 않고 정제된 HTML을 표준출력으로 흘려보냅니다.

사용법:
    python patch_crawler.py <URL> [출력디렉토리]
    python patch_crawler.py <URL> --stdout

예시:
    python patch_crawler.py https://www.leagueoflegends.com/ko-kr/news/game-updates/patch-26-2-notes/
    python patch_crawler.py https://www.leagueoflegends.com/ko-kr/news/game-updates/patch-26-2-notes/ docs/patch
    python patch_crawler.py https://www.leagueoflegends.com/ko-kr/news/game-updates/patch-26-2-notes/ --stdout
"""

import re
import sys
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("필수 패키지가 설치되어 있지 않습니다.")
    print("다음 명령어로 설치해주세요:")
    print("  pip install requests beautifulsoup4")
    sys.exit(1)


def fetch_html(url: str) -> str:
    """URL에서 HTML 콘텐츠를 가져옵니다."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


def extract_patch_container(html: str) -> BeautifulSoup:
    """patch-notes-container 요소를 추출합니다."""
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(id="patch-notes-container")
    if not container:
        raise ValueError("patch-notes-container를 찾을 수 없습니다.")
    return container


def extract_metadata(html: str) -> dict:
    """페이지 메타데이터(게시 날짜)를 추출합니다."""
    soup = BeautifulSoup(html, "html.parser")
    metadata = {}
    time_tag = soup.find("time")
    if time_tag and time_tag.get("datetime"):
        metadata["datetime"] = time_tag["datetime"]
    return metadata


def remove_blockquotes(element: BeautifulSoup) -> BeautifulSoup:
    """모든 blockquote 태그를 제거합니다."""
    for blockquote in element.find_all("blockquote"):
        blockquote.decompose()
    return element


def extract_version_from_url(url: str) -> str:
    """URL에서 패치 버전을 추출합니다."""
    match = re.search(r"patch-(\d+)-(\d+)-notes", url)
    if match:
        return f"{match.group(1)}.{match.group(2)}"
    raise ValueError(f"URL에서 버전을 추출할 수 없습니다: {url}")


def save_html(content: BeautifulSoup, version: str, output_dir: str, url: str = "", metadata: dict = None) -> str:
    """HTML 파일로 저장합니다. 상단에 URL과 datetime 메타 주석을 삽입합니다."""
    output_path = Path(output_dir) / f"{version}.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    if url:
        lines.append(f"<!-- url: {url} -->")
    if metadata and metadata.get("datetime"):
        lines.append(f"<!-- datetime: {metadata['datetime']} -->")
    lines.append(str(content))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return str(output_path)


def render_html(content: BeautifulSoup, url: str = "", metadata: dict = None) -> str:
    """파일에 쓰는 형식과 동일한 HTML 문자열을 만들어 반환합니다."""
    lines = []
    if url:
        lines.append(f"<!-- url: {url} -->")
    if metadata and metadata.get("datetime"):
        lines.append(f"<!-- datetime: {metadata['datetime']} -->")
    lines.append(str(content))
    return "\n".join(lines)


def crawl_patch_notes(url: str, output_dir: str = "docs/patch", to_stdout: bool = False) -> str:
    """패치노트를 크롤링합니다. to_stdout=True이면 HTML을 stdout으로 출력하고, 아니면 파일에 저장합니다."""
    log = (lambda *_: None) if to_stdout else print
    log(f"URL 가져오는 중: {url}")
    html = fetch_html(url)

    log("HTML 파싱 중...")
    container = extract_patch_container(html)
    cleaned = remove_blockquotes(container)
    version = extract_version_from_url(url)
    metadata = extract_metadata(html)

    if to_stdout:
        sys.stdout.write(render_html(cleaned, url=url, metadata=metadata))
        return version
    return save_html(cleaned, version, output_dir, url=url, metadata=metadata)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    url = sys.argv[1]
    rest = sys.argv[2:]
    to_stdout = "--stdout" in rest
    rest = [a for a in rest if a != "--stdout"]
    output_dir = rest[0] if rest else "docs/patch"

    try:
        result = crawl_patch_notes(url, output_dir, to_stdout=to_stdout)
        if not to_stdout:
            print(f"저장 완료: {result}")
    except requests.RequestException as e:
        print(f"네트워크 오류: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"오류 발생: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
