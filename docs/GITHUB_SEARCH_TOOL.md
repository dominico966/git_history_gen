# 🔍 GitHub 저장소 검색 도구 추가

## 📋 문제점

사용자가 저장소 이름만 제공할 때의 문제:

```
User: 타우리 저장소로 설정해줘

AI: ✅ '타우리' 저장소로 설정했습니다
    (실제 GitHub URL을 모름)

User: 현재 저장소 주소

AI: 현재 저장소는 '타우리'입니다
    (문자열 "타우리"만 저장됨, 실제 URL이 아님)
```

**문제**: AI가 실제 GitHub URL을 찾을 수 없음

## ✅ 해결책

### 새로운 도구: `search_github_repository`

GitHub API를 사용하여 저장소 이름으로 실제 저장소 검색

```python
{
    "name": "search_github_repository",
    "description": "GitHub에서 저장소를 검색합니다. 저장소 이름이나 키워드만 알 때 실제 GitHub URL을 찾을 수 있습니다.",
    "parameters": {
        "query": "검색 쿼리 (예: 'tauri', 'rust webview')",
        "max_results": "최대 결과 수 (기본: 5)"
    }
}
```

## 🔧 구현 내용

### 1. `OnlineRepoReader.search_github_repo()`

```python
def search_github_repo(self, query: str, max_results: int = 5) -> Optional[List[Dict]]:
    """
    GitHub에서 저장소 검색
    
    Returns:
        [
            {
                "name": "tauri",
                "full_name": "tauri-apps/tauri",
                "url": "https://github.com/tauri-apps/tauri",
                "clone_url": "https://github.com/tauri-apps/tauri.git",
                "description": "Build smaller, faster...",
                "stars": 85000,
                "language": "Rust",
                "topics": ["desktop", "webview", ...]
            },
            ...
        ]
    """
    # GitHub Search API 사용
    # stars 순으로 정렬
```

**특징:**
- GitHub Search API (`/search/repositories`)
- stars 순으로 정렬
- 이름, URL, 설명, stars, 언어, 토픽 반환

### 2. chat_app.py 통합

```python
# AVAILABLE_TOOLS에 추가
{
    "name": "search_github_repository",
    "description": "GitHub에서 저장소를 검색합니다...",
    ...
}

# execute_online_tools에 구현
async def execute_online_tools(...):
    if function_name == "search_github_repository":
        reader = OnlineRepoReader()
        results = await loop.run_in_executor(
            None,
            reader.search_github_repo,
            query,
            max_results
        )
        
        # 결과 포맷팅
        result_text = f"'{query}' 검색 결과:\n\n"
        for i, repo in enumerate(results, 1):
            result_text += f"{i}. **{repo['full_name']}** ⭐ {repo['stars']}\n"
            result_text += f"   URL: {repo['url']}\n"
            result_text += f"   설명: {repo['description']}\n"
        
        return result_text
```

### 3. 시스템 프롬프트 업데이트

```python
**중요한 규칙:**
- 사용자가 저장소 이름만 제공하면 (예: "타우리", "리액트"):
  1. 먼저 search_github_repository로 정확한 GitHub URL 찾기
  2. 검색 결과에서 가장 적합한 저장소 선택 (stars, 설명 참고)
  3. 찾은 URL로 set_current_repository 실행
- 저장소 URL이 명확하면 바로 set_current_repository 사용
```

## 🎯 사용 시나리오

### 시나리오 1: 이름만 제공
```
User: 타우리 저장소로 설정해줘

AI: 🔧 search_github_repository 실행 중...
      🔍 GitHub 검색: tauri
    ✅ 완료
    
    'tauri' 검색 결과 (5개):
    
    1. **tauri-apps/tauri** ⭐ 85,234
       URL: https://github.com/tauri-apps/tauri
       Clone: https://github.com/tauri-apps/tauri.git
       설명: Build smaller, faster, and more secure desktop applications
       언어: Rust
    
    2. **tauri-apps/tao** ⭐ 1,234
       ...
    
    🔧 set_current_repository 실행 중...
    ✅ 완료
    
    가장 인기있는 'tauri-apps/tauri' 저장소를 설정했습니다!
    ⭐ 85,234개의 star를 받은 Rust 기반 데스크톱 앱 프레임워크입니다.
```

### 시나리오 2: 여러 결과 확인
```
User: rust webview 라이브러리 찾아줘

AI: 🔧 search_github_repository 실행 중...
    ✅ 완료
    
    'rust webview' 검색 결과:
    
    1. **tauri-apps/tauri** ⭐ 85,234
       - 완전한 데스크톱 앱 프레임워크
    
    2. **webview/webview_rust** ⭐ 3,456
       - 간단한 webview 바인딩
    
    3. **wry-rs/wry** ⭐ 2,345
       - 크로스 플랫폼 webview 라이브러리
    
    어떤 걸 사용하시겠어요?
```

### 시나리오 3: 자동 선택
```
User: 리액트 저장소 분석해줘

AI: 🔧 search_github_repository 실행 중...
    ✅ 완료
    
    🔧 set_current_repository 실행 중...
    ✅ 완료
    
    🔧 get_readme 실행 중...
    ✅ 완료
    
    Facebook의 React 라이브러리 (⭐ 220,000)를 분석합니다!
    
    React는 사용자 인터페이스를 만들기 위한 JavaScript 라이브러리...
```

## 📊 장점

### 1. 사용자 편의성
- ✅ "타우리"만 말해도 자동으로 찾음
- ✅ URL 외울 필요 없음
- ✅ 여러 결과 중 선택 가능

### 2. 정확성
- ✅ GitHub API 공식 검색
- ✅ stars 순 정렬 (인기순)
- ✅ 정확한 clone URL 제공

### 3. 추가 정보
- ✅ 설명, stars, 언어, 토픽
- ✅ 프로젝트 개요 빠르게 파악

### 4. 유연성
- ✅ 정확한 이름 (예: "tauri")
- ✅ 키워드 (예: "rust webview")
- ✅ 설명 기반 검색

## 🔍 GitHub API 상세

### Endpoint
```
GET https://api.github.com/search/repositories
```

### Parameters
```python
{
    "q": "tauri",
    "sort": "stars",
    "order": "desc",
    "per_page": 5
}
```

### Response
```json
{
    "items": [
        {
            "name": "tauri",
            "full_name": "tauri-apps/tauri",
            "html_url": "https://github.com/tauri-apps/tauri",
            "description": "Build smaller...",
            "stargazers_count": 85234,
            "language": "Rust",
            "topics": ["desktop", "webview"]
        }
    ]
}
```

## 🎨 사용자 경험

### Before (이름만으로는 불가능)
```
User: 타우리 저장소로 설정해줘
AI: ❌ 저장소 경로나 URL을 정확히 알려주세요
```

### After (자동 검색)
```
User: 타우리 저장소로 설정해줘

AI: [GitHub 검색]
    [가장 적합한 저장소 선택]
    [자동 설정]
    ✅ tauri-apps/tauri 설정 완료!
```

## 📝 변경된 파일

### 1. `src/online_reader.py`
- `OnlineRepoReader.search_github_repo()` 추가
- GitHub Search API 통합

### 2. `src/chat_app.py`
- `AVAILABLE_TOOLS`에 `search_github_repository` 추가
- `execute_online_tools`에 구현
- 시스템 프롬프트 업데이트

## ⚠️ 제한사항

### Rate Limit
- **인증 없음**: 60회/시간
- **인증 있음**: 5,000회/시간

### 개선 가능
```python
# GitHub Token 추가 (선택적)
headers = {
    "Authorization": f"Bearer {github_token}"
}
```

## ✨ 결과

**이제 저장소 이름만 말해도 자동으로 찾아서 설정합니다!**

- ✅ "타우리" → tauri-apps/tauri
- ✅ "리액트" → facebook/react
- ✅ "rust webview" → 여러 결과 제시
- ✅ 자동 URL 변환

**더 편리한 사용자 경험!** 🎉

