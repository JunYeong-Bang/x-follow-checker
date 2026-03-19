# X 일방 팔로우 검사기

내가 팔로우하는 목록과 나를 팔로우하는 목록을 비교해서 아래를 구합니다.

- 일방 팔로우(`one_way_following`)
- 맞팔(`mutuals`)
- 일방 팔로워(`one_way_followers`)

## 사용방법

X에서 내 데이터 아카이브를 받아서 비교합니다.

1. X 설정에서 "내 데이터 다운로드" 요청
2. 받은 아카이브(zip) 파일을 GUI로 업로드

## 실행파일(.exe) 사용

빌드된 실행파일은 아래 경로에 생성됩니다.

`dist\\XFollowChecker.exe`

실행만 하면 바로 GUI가 열립니다.

```bash
dist\\XFollowChecker.exe
```

새 실행파일을 다시 만들 때는 아래를 실행하세요.

```bash
build_exe.bat
```

## GitHub Releases에서 받기

태그를 푸시하면 GitHub Actions가 자동으로 exe를 빌드해서 Releases에 첨부합니다.

1. 새 버전 태그 생성
2. 태그 푸시
3. Releases에서 `XFollowChecker-windows-x64.exe` 다운로드

예시:

```bash
git tag v1.0.1
git push origin v1.0.1
```

Releases 페이지:

https://github.com/JunYeong-Bang/x-follow-checker/releases

## exe 실행 선행 조건

- Windows 10/11 x64 권장
- 별도 Python 설치 불필요 (exe에 포함됨)
- 인터넷 연결 권장 (프로필 이미지 URL 로드 시 사용)
- 처음 실행 시 Windows SmartScreen 경고가 나오면 `추가 정보` -> `실행`으로 진행
- 드물게 DLL 관련 오류가 나면 `Microsoft Visual C++ Redistributable 2015-2022 (x64)` 설치 후 재실행

### GUI로 파일 업로드해서 보기

zip 파일을 선택하면 결과를 탭별 리스트로 바로 확인할 수 있습니다.

```bash
python gui_app.py
```

실행 후:

1. `파일 선택` 클릭
2. X 아카이브 zip 선택
3. `분석` 클릭

탭 구성:

- 일방 팔로우
- 맞팔
- 일방 팔로워

## 참고

- 사용자명은 소문자로 정규화해서 비교합니다.
- 아카이브 파일 구조가 계정/시점에 따라 조금 다를 수 있습니다.
