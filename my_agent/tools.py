import requests
from bs4 import BeautifulSoup
import os
import json
import re


# ── 파일 읽기 ──────────────────────────────────────────────────────────────────
def read_file(filename: str) -> str:
    """텍스트 파일을 읽어 내용을 반환한다."""
    if not os.path.exists(filename):
        return f"[오류] '{filename}' 파일이 존재하지 않습니다."
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()


# ── 파일 쓰기 (새로 생성 또는 덮어쓰기) ──────────────────────────────────────
def write_file(filename: str, content: str) -> str:
    """내용을 파일에 저장한다. 파일이 없으면 새로 생성한다."""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    return f"[완료] '{filename}' 파일에 저장했습니다."


# ── 파일 수정 (기존 내용에 추가) ──────────────────────────────────────────────
def append_file(filename: str, content: str) -> str:
    """기존 파일 끝에 내용을 추가한다."""
    with open(filename, "a", encoding="utf-8") as f:
        f.write("\n" + content)
    return f"[완료] '{filename}' 파일에 내용을 추가했습니다."


# ── 나무위키 검색 ──────────────────────────────────────────────────────────────
def search_namuwiki(keyword: str) -> str:
    """나무위키에서 키워드를 검색하여 본문 텍스트를 반환한다."""
    url = f"https://namu.wiki/w/{requests.utils.quote(keyword)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return f"[오류] 나무위키에서 '{keyword}'를 찾을 수 없습니다. (HTTP {response.status_code})"

        soup = BeautifulSoup(response.text, "html.parser")

        # 방법 1: <script> 태그 안의 JSON 데이터에서 본문 추출
        # 나무위키는 초기 렌더링 데이터를 __INITIAL_STATE__ 또는 유사한 변수에 담음
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string and "INITIAL_STATE" in script.string:
                # JSON 추출 시도
                match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*\})', script.string, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        # 본문 텍스트 찾기
                        content = _extract_from_json(data)
                        if content and len(content) > 100:
                            return f"=== 나무위키: {keyword} ===\n{content[:3000]}"
                    except Exception:
                        pass

        # 방법 2: <article> 또는 메인 콘텐츠 태그 직접 추출
        article = soup.find("article")
        if article:
            # 불필요한 태그 제거
            for tag in article.find_all(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = article.get_text(separator="\n", strip=True)
            text = _clean_text(text)
            if len(text) > 100:
                return f"=== 나무위키: {keyword} ===\n{text[:3000]}"

        # 방법 3: 모든 <p>, <h2>, <h3> 태그에서 텍스트 수집
        tags = soup.find_all(["h1", "h2", "h3", "p"])
        lines = []
        for tag in tags:
            t = tag.get_text(strip=True)
            # 라이선스/공지 텍스트 필터링
            if t and len(t) > 10 and not any(skip in t for skip in [
                "CC BY", "reCAPTCHA", "hCaptcha", "Privacy Policy",
                "Terms of Service", "나무위키는 위키위키", "저작권은 각 기여자"
            ]):
                lines.append(t)

        text = "\n".join(lines)
        if len(text) > 50:
            return f"=== 나무위키: {keyword} ===\n{text[:3000]}"

        return f"[오류] '{keyword}' 페이지에서 본문을 추출하지 못했습니다. 나무위키가 JS 렌더링을 사용하여 내용 추출이 제한됩니다."

    except requests.exceptions.RequestException as e:
        return f"[오류] 네트워크 오류: {e}"


def _extract_from_json(data: dict, depth: int = 0) -> str:
    """JSON 데이터에서 재귀적으로 텍스트 콘텐츠를 찾는다."""
    if depth > 5:
        return ""
    if isinstance(data, str) and len(data) > 200:
        return data
    if isinstance(data, dict):
        for key in ["content", "body", "text", "wikitext", "source"]:
            if key in data and isinstance(data[key], str) and len(data[key]) > 200:
                return data[key]
        for val in data.values():
            result = _extract_from_json(val, depth + 1)
            if result:
                return result
    if isinstance(data, list):
        for item in data:
            result = _extract_from_json(item, depth + 1)
            if result:
                return result
    return ""


def _clean_text(text: str) -> str:
    """불필요한 줄바꿈과 공백을 정리한다."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    # 라이선스/공지 필터링
    filtered = [l for l in lines if not any(skip in l for skip in [
        "CC BY", "reCAPTCHA", "hCaptcha", "Privacy Policy",
        "Terms of Service", "나무위키는 위키위키", "저작권은 각 기여자",
        "This site is protected"
    ])]
    return "\n".join(filtered)


# ── 툴 목록 (에이전트에 전달할 스키마) ────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_namuwiki",
            "description": "나무위키에서 키워드를 검색하여 해당 문서의 내용을 가져온다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "검색할 키워드"}
                },
                "required": ["keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "로컬 텍스트 파일을 읽어 내용을 반환한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "읽을 파일명 (예: result.txt)"}
                },
                "required": ["filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "내용을 파일에 저장한다. 파일이 없으면 새로 생성한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "저장할 파일명"},
                    "content": {"type": "string", "description": "저장할 내용"}
                },
                "required": ["filename", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "append_file",
            "description": "기존 파일 끝에 내용을 추가한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "수정할 파일명"},
                    "content": {"type": "string", "description": "추가할 내용"}
                },
                "required": ["filename", "content"]
            }
        }
    }
]