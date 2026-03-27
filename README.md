# My Agent - Multi-step Tool Calling Agent

이 프로젝트는 Ollama 로컬 LLM 환경을 활용하여 사용자의 요청에 따라 상황에 맞는 툴(도구)을 여러 단계에 걸쳐 호출하고 결과를 파일 등에 저장할 수 있는 커스텀 툴 콜링 AI 에이전트입니다.
기본 모델로 `qwen2.5-coder:7b`를 사용하며, 나무위키 문서 검색 및 로컬 파일 읽기/쓰기 기능을 지원합니다.

## 필수 요건 (Prerequisites)

- **Python 3.8+**
- **Ollama**: 컴퓨터에 Ollama 애플리케이션이 설치되어 구동 중이어야 합니다 (`ollama serve`).
  - [Ollama 홈페이지](https://ollama.com/)에서 다운로드 가능
  - 설치 후 터미널(또는 명령 프롬프트)에서 해당 모델을 다운로드해주세요.
    ```bash
    ollama pull qwen2.5-coder:7b
    ```

## 설치 방법 (Installation)

1. 프로젝트 폴더로 이동합니다.
2. 만약 가상환경(venv 등)을 사용한다면 활성화해주세요.
3. 다음 명령어를 실행하여 필요한 패키지(`requests`, `beautifulsoup4`, `ollama` 등)를 설치합니다:

```bash
pip install -r requirements.txt
```

## 실행 방법 (How to Run)

Ollama 서버가 실행 중인지 확인한 후, 아래 명령어로 에이전트를 곧바로 실행할 수 있습니다.

```bash
python agent.py
```

`agent.py` 코드를 수정 없이 실행하면, **"리그 오브 레전드 라는 게임에 대해 검색하고 결과를 lol.txt 파일에 저장해줘"** 라는 기본 요청이 수행됩니다.
원하는 작업이나 검색어가 있다면 `agent.py` 파일 하단의 `run_agent(...)` 부분에 있는 사용자 입력 텍스트를 수정하여 실행해 주시면 됩니다.

---

## 제공되는 기능 및 도구 (Tools)

AI 에이전트는 상황에 따라 스스로 다음과 같은 도구(`tools.py`에 정의됨)들을 선별하고 조합하여 사용합니다.

- **`search_namuwiki(keyword)`**: `beautifulsoup4`와 `requests`를 사용해 나무위키에서 특정 키워드를 검색하고 관련된 본문을 추출하여 가져옵니다.
- **`read_file(filename)`**: 작업 디렉터리에 있는 로컬 텍스트 파일의 내용을 읽어옵니다.
- **`write_file(filename, content)`**: 검색 결과 등의 텍스트를 새로운 파일로 저장하거나 기존 파일의 내용을 덮어씁니다.
- **`append_file(filename, content)`**: 텍스트 파일의 맨 끝에 새로운 내용을 이어서 추가합니다.

## 작동 원리 (How it works)
1. **입력:** 코드 상의 `run_agent`에 있는 사용자 요청을 LLM(`qwen2.5-coder`)에 넘깁니다.
2. **도구 선택:** LLM은 JSON 형태(`tool_calls`)로 어떠한 도구를 쓸지, 도구의 인자 값은 무엇일지 결정하여 에이전트에게 지시합니다.
3. **도구 실행 및 결과 반영:** 코드 내부에서 파이썬 함수가 실행되고, 해당 결과를 다시 대화 기록(`messages`)에 추가하여 LLM에게 넘겨줍니다.
4. **결과 요약:** 원하는 결과가 나올 때까지 이 과정을 자동으로 반복(최대 5 스텝)한 뒤, 작업이 완료되면 최종 문장 형태의 결과를 도출해 냅니다.
