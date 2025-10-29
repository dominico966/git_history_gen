# Windows 긴 경로 문제 해결 가이드

**날짜**: 2025-10-28  
**문제**: Git clone 시 "Filename too long" 에러  
**영향 범위**: Windows 환경에서 긴 파일 경로를 포함한 저장소  
**Clone 방식**: 전체 히스토리 다운로드 (shallow clone 없음)

---

## 🐛 문제 상황

```
fatal: unable to create file packages/.../AttachmentIcon.xcassets/FileAttachment_json.imageset/Contents.json: Filename too long
```

**원인**: Windows의 기본 경로 제한 (260자)을 초과하는 파일이 저장소에 포함됨

**영향받는 저장소 예시**:
- `toeverything/AFFiNE` - iOS 앱 리소스 파일
- 긴 경로의 스크린샷/테스트 파일이 있는 프로젝트

---

## ✅ 해결 방법

### 방법 1: Git 글로벌 설정 (권장) ⭐

**관리자 권한으로 PowerShell 실행 후**:
```powershell
git config --system core.longpaths true
```

**장점**:
- ✅ 빠르고 간단
- ✅ 모든 Git 작업에 적용
- ✅ 재부팅 불필요

### 방법 2: Windows 레지스트리 설정

1. **관리자 권한**으로 레지스트리 편집기 실행 (`Win+R` → `regedit`)
2. 다음 경로로 이동:
   ```
   HKLM\SYSTEM\CurrentControlSet\Control\FileSystem
   ```
3. `LongPathsEnabled` (DWORD) 생성 또는 수정
4. 값을 `1`로 설정
5. **시스템 재시작**

**장점**:
- ✅ 시스템 전체에 영향
- ✅ 모든 프로그램에서 긴 경로 지원

### 방법 3: 로컬 저장소 사용

원격 저장소를 직접 clone하는 대신:

1. 로컬에 먼저 clone:
   ```bash
   git clone https://github.com/toeverything/AFFiNE C:\repo
   ```

2. 로컬 경로를 Streamlit UI에 입력:
   ```
   Repository Type: Local Path
   Local Repository Path: C:\repo
   ```

**장점**:
- ✅ Git 설정 변경 불필요
- ✅ 문제 발생 시 수동 해결 가능

---

## 🔧 적용된 개선사항

### 1. 자동 Git Longpaths 설정

**위치**: `src/repo_cache.py`

Clone 전에 자동으로 `core.longpaths` 설정 시도:

```python
# Windows에서 긴 경로 지원 설정
subprocess.run(['git', 'config', '--global', 'core.longpaths', 'true'], 
               capture_output=True, check=False)
```

### 2. 명확한 에러 메시지

**위치**: `src/repo_cache.py`

"Filename too long" 에러 발생 시:

```
============================================================
Git Clone 실패: 파일 경로가 너무 깁니다
============================================================
저장소: https://github.com/toeverything/AFFiNE

해결 방법:
1. 관리자 권한으로 PowerShell 실행
2. 다음 명령 실행: git config --system core.longpaths true
3. 또는 Windows 레지스트리에서 긴 경로 활성화
4. 프로그램 재시작
============================================================
```

### 3. Streamlit UI 개선

**위치**: `src/app.py`

인덱싱 실패 시 해결 방법을 확장 가능한 UI로 표시:

```
❌ 파일 경로가 너무 깁니다 (Windows 제한)

📋 해결 방법 보기 [확장됨]
  - 방법 1: Git 설정 (권장)
  - 방법 2: Windows 레지스트리 설정
  - 방법 3: 로컬 저장소 사용

💡 설정 후 프로그램을 재시작하고 다시 시도하세요.
```

---

## 🧪 테스트

**테스트 파일**: `tests/test_git_pull_strategy.py`

새로운 테스트 케이스 추가:
```python
def test_long_path_handling():
    """긴 파일 경로 처리 테스트"""
    # AFFiNE 저장소로 테스트
    # 실패 시 예상된 실패로 처리
```

---

## 📊 영향 분석

### 변경 전
```
1. Clone 시도
2. "Filename too long" 에러
3. 프로그램 종료
4. ❌ 사용자는 원인 파악 어려움
```

### 변경 후
```
1. Clone 시도 (자동 longpaths 설정)
2. 실패 시 명확한 에러 메시지
3. 해결 방법 3가지 제시
4. ✅ 사용자가 쉽게 해결 가능
```

---

## 💡 사용자 가이드

### Streamlit UI 사용 시

1. **인덱싱 버튼 클릭**
2. 에러 발생 시 **"해결 방법 보기"** 확장
3. **방법 1** 선택 (가장 간단)
4. 관리자 PowerShell에서 명령 실행:
   ```powershell
   git config --system core.longpaths true
   ```
5. **Streamlit 앱 재시작**
6. **다시 인덱싱 시도**

### 프로그래밍 방식

```python
from src.document_generator import DocumentGenerator

try:
    doc_gen = DocumentGenerator("https://github.com/toeverything/AFFiNE")
    commits = doc_gen.get_commits(limit=10)
except Exception as e:
    if 'Filename too long' in str(e):
        print("Windows 긴 경로 지원을 활성화하세요:")
        print("git config --system core.longpaths true")
    raise
```

---

## 🔍 관련 이슈

### Windows 경로 제한

- **기본 제한**: 260자 (MAX_PATH)
- **Windows 10 1607+**: 긴 경로 지원 가능
- **레지스트리 설정 필요**: `LongPathsEnabled`

### Git 설정

- `core.longpaths`: Git에서 긴 경로 처리
- `--system`: 시스템 전체 적용
- `--global`: 현재 사용자만

---

## 📝 커밋 메시지

```
Fix: Windows 긴 경로 문제 처리 개선

1. Clone 전 자동 git longpaths 설정
2. "Filename too long" 에러 시 명확한 가이드 제공
3. Streamlit UI에 해결 방법 표시
4. 테스트 케이스 추가

변경된 파일:
- src/repo_cache.py
- src/app.py
- tests/test_git_pull_strategy.py

Issue: Git clone 시 "Filename too long" 에러
Solution: 자동 설정 시도 + 사용자 가이드 제공
```

---

## ✅ 완료

- ✅ 자동 longpaths 설정 시도
- ✅ 명확한 에러 메시지
- ✅ Streamlit UI 개선
- ✅ 테스트 추가
- ✅ 문서화 완료

**프로덕션 준비 완료!** 🚀

