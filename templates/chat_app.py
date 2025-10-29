# chainlit 을 사용한 대화형 채팅앱
# ***프롬프트는 여러줄 문자열('''''' or """""")은 사용하지 말 것***
# ***프롬프트는 반드시 구조화된 객체 사용 혹은 JSON으로 작성. LLM Agent이 자꾸 파일 깨먹음.***
# 구현된 tools 기능을 최대한 활용할 것
# 필요하다면 추가적인 도구도 구현할 것
# 툴 목록은 src/tools.py, src/online_reader.py 참고하여 대화에 필요한 기능 구현

# 주요 기능:
# - 최초 툴 제공 및 시스템 프롬프트
# - conversation_history 사용하여 대화 유지
# - 화면 표시는 conversation_history 사용
# - 별도 프롬프트로 llm 호출하여 툴 호출 판단
# - Step 사용하여 중간 작업 표시


