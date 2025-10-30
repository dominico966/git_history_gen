# 🚀 온라인 파일 읽기 도구 추가 완료

## 📋 새로운 기능

인덱싱된 커밋 정보 외에도 **온라인에서 직접 파일 내용을 읽고 추가 컨텍스트를 제공**하는 도구들을 추가했습니다.

## ✨ 추가된 도구들

### 1. `get_readme` 
**프로젝트 개요 파악**
- 저장소의 README 파일을 읽어서 프로젝트 설명, 사용법, 아키텍처 등을 제공
- 새로운 저장소를 빠르게 이해하는데 유용

```python
# 사용 예
AI: 🔧 get_readme 실행 중...
    📚 README 찾는 중...
    ✅ 완료
    
    README:
    
    # Tauri
    
    Build an optimized, secure, and frontend-independent application 
    for multi-platform deployment...
```

### 2. `read_file_from_commit`
**특정 커밋의 파일 전체 읽기**
- 커밋 해시와 파일 경로를 지정하여 해당 시점의 파일 전체 내용 확인
- 코드 리뷰, 상세 분석에 유용

```python
# 사용 예
User: abc123 커밋에서 src/main.rs 파일 내용을 보여줘

AI: 🔧 read_file_from_commit 실행 중...
    📄 파일: src/main.rs
    📌 커밋: abc123
    📖 읽는 중...
    ✅ 완료
    
    파일 'src/main.rs' (커밋 abc123):
    
    ```rust
    fn main() {
        tauri::Builder::default()
            .run(tauri::generate_context!())
            .expect("error while running tauri application");
    }
    ```
```

### 3. `get_file_context`
**변경된 파일의 diff와 컨텍스트**
- 커밋에서 변경된 파일의 diff (추가/삭제된 라인)
- 전체 파일 내용 (짧은 경우)
- 변경 통계 (추가/삭제 라인 수)

```python
# 사용 예
User: 최근 커밋에서 config.rs가 어떻게 바뀌었어?

AI: 🔧 get_file_context 실행 중...
    📄 파일: config.rs
    🔍 변경 내역 분석 중...
    ✅ 완료
    
    파일: config.rs (커밋 def456)
    
    변경 사항:
    ```diff
    - const DEFAULT_PORT: u16 = 8080;
    + const DEFAULT_PORT: u16 = 3000;
    + const MAX_CONNECTIONS: usize = 100;
    ```
    
    추가: 2줄, 삭제: 1줄
```

### 4. `read_github_file`
**GitHub URL에서 직접 파일 읽기**
- GitHub 파일 URL을 주면 API를 통해 최신 내용 가져오기
- 빠른 파일 확인에 유용

```python
# 사용 예
User: https://github.com/tauri-apps/tauri/blob/dev/core/tauri/Cargo.toml 이 파일 보여줘

AI: 🔧 read_github_file 실행 중...
    🌐 URL: https://github.com/tauri-apps/tauri/blob/dev/...
    📥 다운로드 중...
    ✅ 완료
    
    파일 내용:
    
    ```toml
    [package]
    name = "tauri"
    version = "2.0.0"
    ...
    ```
```

## 🔧 기술 구현

### 1. 새로운 모듈: `src/online_reader.py`

#### `OnlineRepoReader` 클래스
- **GitHub API 통합**: `api.github.com`을 통해 파일 가져오기
- **URL 파싱**: GitHub URL 자동 분석
- **Base64 디코딩**: GitHub API 응답 처리

#### 유틸리티 함수들
- `read_file_from_commit()`: GitPython으로 특정 커밋의 파일 읽기
- `get_file_context()`: diff 생성 및 변경 통계
- `get_readme_content()`: README 파일 자동 찾기

### 2. `chat_app.py` 통합

#### Function Calling에 추가
```python
AVAILABLE_TOOLS = [
    # ... 기존 도구들 ...
    {
        "name": "get_readme",
        "description": "저장소의 README를 읽어 프로젝트 개요 제공"
    },
    {
        "name": "read_file_from_commit",
        "description": "특정 커밋의 파일 전체 내용 읽기"
    },
    {
        "name": "get_file_context",
        "description": "변경된 파일의 diff와 컨텍스트"
    },
    {
        "name": "read_github_file",
        "description": "GitHub URL에서 직접 파일 읽기"
    }
]
```

#### `execute_online_tools()` 함수
- 온라인 읽기 도구들을 별도로 처리
- 비동기 실행 및 진행 상황 표시
- 긴 파일은 자동으로 미리보기 (3000자)

### 3. 시스템 프롬프트 강화

```python
**추가 컨텍스트 도구 (온라인 읽기):**
8. get_readme: 저장소의 README를 읽어 프로젝트 개요 파악
9. read_file_from_commit: 특정 커밋의 파일 전체 내용 읽기
10. get_file_context: 커밋에서 변경된 파일의 diff와 컨텍스트
11. read_github_file: GitHub URL에서 직접 파일 읽기

**중요한 규칙:**
- 저장소를 처음 분석할 때 get_readme로 개요 파악
- 상세한 코드 분석이 필요하면 온라인 읽기 도구 적극 활용
- 변경 내용의 영향을 파악하려면 get_file_context 사용
```

## 📊 사용 시나리오

### 시나리오 1: 새 저장소 빠른 이해
```
User: https://github.com/tauri-apps/tauri 이게 뭐야?

AI: 1. set_current_repository ✅
    2. get_readme ✅
    
    Tauri는 Rust로 작성된 크로스 플랫폼 데스크톱 애플리케이션 
    프레임워크입니다. 웹 기술(HTML/CSS/JS)로 UI를 만들고, 
    백엔드는 Rust로 구현하여 가볍고 안전한 네이티브 앱을 만들 수 있습니다.
    
    주요 특징:
    - 작은 번들 사이즈 (< 600KB)
    - 메모리 안전성 (Rust)
    - 멀티 플랫폼 (Windows/macOS/Linux)
```

### 시나리오 2: 커밋 상세 분석
```
User: abc123 커밋에서 뭐가 바뀌었는지 자세히 알려줘

AI: 1. get_commit_summary (해당 커밋) ✅
    2. get_file_context (주요 파일들) ✅
    
    커밋 abc123 "Fix memory leak in window manager":
    
    주요 변경:
    - src/window.rs: 메모리 누수 수정
      - Drop trait 구현 추가
      - 리소스 정리 로직 강화
    
    상세 변경 내역:
    ```diff
    + impl Drop for Window {
    +     fn drop(&mut self) {
    +         self.cleanup_resources();
    +     }
    + }
    ```
```

### 시나리오 3: 특정 파일 코드 리뷰
```
User: Cargo.toml 파일 보여줘

AI: 🔧 read_file_from_commit 실행...
    
    Cargo.toml:
    ```toml
    [package]
    name = "tauri"
    version = "2.0.0"
    
    [dependencies]
    serde = { version = "1.0", features = ["derive"] }
    ...
    ```
    
    의존성이 잘 정리되어 있네요. serde는 직렬화에, 
    tokio는 비동기 런타임에 사용됩니다.
```

## 🎯 장점

### 1. 풍부한 컨텍스트
- ✅ 인덱싱된 요약 정보
- ✅ 실제 파일 전체 내용
- ✅ 변경 사항 diff
- ✅ 프로젝트 README

### 2. 유연한 분석
- ✅ 인덱싱 없이도 파일 읽기 가능
- ✅ 특정 시점(커밋)의 파일 확인
- ✅ GitHub API 활용으로 빠른 접근

### 3. 사용자 경험
- ✅ "이 파일 보여줘" → 바로 표시
- ✅ "뭐가 바뀌었어?" → diff 표시
- ✅ "프로젝트 설명해줘" → README 읽고 요약

### 4. 캐시 활용
- ✅ `RepoCloneCache` 활용으로 빠른 접근
- ✅ 로컬/원격 저장소 모두 지원
- ✅ GitPython으로 안정적인 파일 읽기

## 📝 변경된 파일

### 신규 파일
1. **`src/online_reader.py`** (290 lines)
   - `OnlineRepoReader` 클래스
   - GitHub API 통합
   - 파일 읽기 유틸리티 함수들

### 수정된 파일
2. **`src/chat_app.py`**
   - `AVAILABLE_TOOLS`에 4개 도구 추가
   - `execute_online_tools()` 함수 추가
   - `execute_tool()`에 라우팅 로직
   - 시스템 프롬프트 업데이트

## 🚀 사용 방법

### 기본 사용
```
# README 읽기
User: 이 프로젝트가 뭐야?
AI: [자동으로 get_readme 실행]

# 파일 읽기
User: src/main.rs 파일 보여줘
AI: [read_file_from_commit 실행]

# diff 확인
User: 최근 커밋에서 config 파일이 어떻게 바뀌었어?
AI: [get_file_context 실행]

# GitHub URL
User: https://github.com/.../file.py 이거 보여줘
AI: [read_github_file 실행]
```

### 명시적 호출 (명령어 모드)
```bash
# 아직 명령어 모드 미구현 (Function Calling만 사용)
# 필요시 추가 가능
```

## ⚠️ 제한사항

### 1. 파일 크기
- 3000자 이상은 자동으로 미리보기
- LLM 컨텍스트 길이 제한 고려

### 2. GitHub API
- Rate limit 존재 (인증 없이 60회/시간)
- 필요시 GitHub token 추가 가능

### 3. 지원 플랫폼
- 현재 GitHub 위주 지원
- GitLab, Bitbucket 추가 가능

## ✨ 향후 개선 가능

1. **GitHub Token 지원**: API rate limit 증가
2. **GitLab/Bitbucket 지원**: 다른 플랫폼 추가
3. **파일 검색**: 저장소 내 파일 이름으로 검색
4. **디렉토리 구조**: 프로젝트 구조 트리 표시
5. **코드 하이라이팅**: 구문 강조 표시
6. **이미지/바이너리**: 바이너리 파일 처리

---

## 🎉 결론

**이제 AI가 인덱싱된 정보뿐만 아니라 실제 파일 내용까지 읽고 분석할 수 있습니다!**

- ✅ 프로젝트 개요 (README)
- ✅ 특정 파일 전체 내용
- ✅ 변경 사항 diff
- ✅ GitHub 직접 접근

**더 풍부하고 정확한 Git 히스토리 분석이 가능합니다!** 🚀✨

# 온라인 리더 도구(요약)

- `get_readme(repo_url)`: 원격 README 빠른 요약
- `read_github_file(url)`: GitHub 단일 파일 직접 읽기
- `read_file_from_commit(repo, sha, path)`: 특정 커밋의 파일 내용
- `get_file_context(repo, sha, path)`: 변경 타입/주요 hunk 포함 컨텍스트
- `get_commit_diff(repo, sha, max_files)`: 커밋 전체 diff(파일 최대 N개)

팁
- 짧은 SHA(7~10자리)도 자동 해석 시도
- shallow 상태면 자동 deepen 후 재시도
- 출력이 큰 경우 일부만 요약하여 표시
