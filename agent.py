import json
import re
import ollama
from tools import TOOLS, search_namuwiki, read_file, write_file, append_file


# ── 툴 실행 함수 ───────────────────────────────────────────────────────────────
def execute_tool(tool_name: str, tool_args: dict) -> str:
    """툴 이름과 인자를 받아 해당 함수를 실행하고 결과를 반환한다."""
    print(f"\n  툴 실행: {tool_name}({tool_args})")

    if tool_name == "search_namuwiki":
        return search_namuwiki(**tool_args)
    elif tool_name == "read_file":
        return read_file(**tool_args)
    elif tool_name == "write_file":
        return write_file(**tool_args)
    elif tool_name == "append_file":
        return append_file(**tool_args)
    else:
        return f"[오류] 알 수 없는 툴: {tool_name}"


# ── 텍스트에서 tool call JSON 파싱 (fallback) ──────────────────────────────────
def parse_tool_calls_from_text(text: str) -> list:
    """
    LLM이 tool_calls 형식 대신 JSON 텍스트로 툴 호출을 출력한 경우,
    텍스트에서 {"name": ..., "arguments": {...}} 패턴을 파싱하여 반환한다.
    """
    pattern = r'\{\s*"name"\s*:\s*"(\w+)"\s*,\s*"arguments"\s*:\s*(\{.*?\})\s*\}'
    matches = re.findall(pattern, text, re.DOTALL)

    tool_calls = []
    for name, args_str in matches:
        try:
            args = json.loads(args_str)
            tool_calls.append({"function": {"name": name, "arguments": args}})
        except json.JSONDecodeError:
            pass
    return tool_calls


# ── 메인 에이전트 루프 ─────────────────────────────────────────────────────────
def run_agent(user_input: str):
    """
    Multi-step Tool Calling 에이전트.

    동작 원리:
    1. 사용자 입력을 LLM에 전달한다.
    2. LLM이 tool_calls를 포함한 응답을 반환하면 해당 툴을 실행한다.
       (tool_calls가 없더라도 텍스트에서 JSON 툴 호출 패턴을 파싱하는 fallback 적용)
    3. 툴 실행 결과를 'tool' 역할의 메시지로 대화 히스토리에 추가한다.
    4. 업데이트된 히스토리를 다시 LLM에 전달한다.
    5. LLM이 tool_calls 없이 최종 텍스트 응답을 반환할 때까지 2~4를 반복한다.
    """
    print(f"\n{'='*55}")
    print(f"사용자: {user_input}")
    print(f"{'='*55}")

    messages = [
        {
            "role": "system",
            "content": (
                "당신은 유용한 AI 에이전트입니다. "
                "사용자의 요청을 처리하기 위해 필요한 툴을 순서대로 호출하세요. "
                "나무위키 검색 결과는 반드시 파일에 저장하세요."
            )
        },
        {"role": "user", "content": user_input}
    ]

    max_steps = 5
    last_search_result = None  # 마지막 검색 결과 보관

    for step in range(max_steps):
        print(f"\n[Step {step + 1}] LLM 호출 중...")

        response = ollama.chat(
            model="qwen2.5-coder:7b",
            messages=messages,
            tools=TOOLS
        )

        message = response["message"]
        tool_calls = message.get("tool_calls") or []

        # tool_calls가 없으면 텍스트에서 파싱 시도 (fallback)
        if not tool_calls and message.get("content"):
            tool_calls = parse_tool_calls_from_text(message["content"])
            if tool_calls:
                print("  tool_calls 미지원 → 텍스트에서 툴 호출 파싱 성공")

        if not tool_calls:
            print(f"\n에이전트 최종 답변:\n{message['content']}")
            break

        messages.append({"role": "assistant", "content": message.get("content", "")})

        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            tool_args = tool_call["function"]["arguments"]

            # 체이닝: write_file content가 플레이스홀더면 실제 검색 결과로 교체
            if tool_name in ("write_file", "append_file") and last_search_result:
                content = tool_args.get("content", "")
                is_placeholder = (
                    "{{" in content
                    or "[" in content
                    or len(content) < 50
                )
                if is_placeholder:
                    tool_args["content"] = last_search_result
                    print("  체이닝: 검색 결과를 파일 내용으로 자동 연결")

            result = execute_tool(tool_name, tool_args)

            if tool_name == "search_namuwiki":
                last_search_result = result

            print(f"  결과 미리보기: {result[:200]}")

            messages.append({
                "role": "tool",
                "content": result
            })

    else:
        print("\n[경고] 최대 툴 호출 횟수에 도달했습니다.")


# ── 실행 ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run_agent("리그 오브 레전드 라는 게임에 대해 검색하고 결과를 lol.txt 파일에 저장해줘")