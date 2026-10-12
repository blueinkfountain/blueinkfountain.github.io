# Blueink 수학 블로그

Jekyll + Just the Docs로 운영하는 수학 문서, PDF 필기와 ODE 실험 도구입니다.

## 폴더와 원본

| 경로 | 용도 |
| --- | --- |
| `docs/` | 게시 페이지. URL 호환성을 위해 기존 경로를 유지합니다. |
| `assets/pdfs/` | 기존 공개 수학 PDF. 파일명을 바꿀 때 연결 페이지도 수정합니다. |
| `assets/euler-method/` | ODE Lab의 유일한 JavaScript/CSS 원본 |
| `scripts/` | 필기 갱신·기록 편집·검증 코드 |
| `tests/` | 실제 운영 파일을 검사하는 Python/Node 테스트 |
| `untexed/YYMMDD/` | 로컬 필기 스냅샷. Git에 올리지 않습니다. |
| `untexed-current/` | 최신 공개 필기. 생성 결과를 Git에 올립니다. |
| `_data/untexed_records.yml` | 학습 기록과 잉크 통계. 과거 기록의 보존 원본입니다. |
| `_ink_reference/` | 잉크 계산 기준 PDF. 변경하면 계산 기준도 달라집니다. |
| `.cache/` | 재생성 가능한 계산 캐시 및 갱신 복구 정보 |
| `.archive/` | 이전 설치 패키지·백업·LaTeX 원본의 로컬 보관소. Git/배포 제외 |
| `maintenance/` | 운영 변경 계획·검증 기록. 배포 제외 |

`daily_record_note/`, `ode_lab_timeline_fix/` 같은 설치용 코드 복사본은 더 이상 편집하지 않습니다.
예전 설치 자료는 `.archive/2026-10-12/`와 전체 백업에 보존했습니다.

## 개발 환경

Python 3.9 이상, Node.js 20 이상, Ruby 3.3을 사용합니다. CI는 Python 3.11 / Node 22 / Ruby 3.3입니다.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-gui.txt
bundle config set --local path vendor/bundle
bundle install
```

macOS의 기본 Ruby가 오래된 경우 Homebrew Ruby를 사용합니다.

```sh
brew install ruby@3.3
export PATH="/opt/homebrew/opt/ruby@3.3/bin:$PATH"
```

GUI 없이 검사만 할 때는 `requirements.txt`만 설치하면 됩니다. Node 테스트에는 추가 npm 패키지가 필요 없습니다.

## 필기 갱신

1. `untexed/YYMMDD/`에 **그날 전체 필기**를 넣습니다. 부분 변경분만 넣으면 나머지 파일이 삭제된 것으로 기록됩니다.
2. 저장소 루트에서 `./update-notes.sh`를 실행하고 Daily Record에 기록을 입력합니다.
3. 검사를 실행하고 Git diff에서 기록·PDF 변경을 검토합니다.
4. 원하는 변경을 커밋하고 main에 push하면 검증 → 빌드 → 배포가 실행됩니다.

```sh
./update-notes.sh
.venv/bin/python scripts/check_site.py
git status --short
git diff --stat
```

`update-notes.sh`는 기록 YAML과 공개 필기만 스테이징합니다. 자동 커밋·push는 하지 않습니다.
기존 개인 셸 명령 `update!`는 저장소 밖 설정이므로 이 저장소의 필수 명령으로 삼지 않습니다.
Git hook 설치 없이도 위 명령으로 같은 작업을 할 수 있습니다.

최근 3개 스냅샷과 그 직전 비교 기준 1개가 갱신에 필요합니다. 이전 기록은 YAML에 동결됩니다.
과거 로컬 스냅샷은 자동 삭제하지 않습니다. 삭제하려면 별도 백업과 필요한 비교 날짜를 먼저 확인하세요.

## 블로그 디자인과 문서 구성

기존 사이드바·메뉴·PDF 뷰어를 유지합니다. 파일 관리 작업에서는 `_includes/head_custom.html`,
문서 front matter, 메뉴 노출 여부, PDF 임베드 방식 등을 임의로 변경하지 않습니다.
기존 문서와 같은 형식으로 새 문서를 작성하고, 디자인 변경은 별도 요청이 있을 때만 합니다.

`check_site.py`와 `check_build.py`는 기존 미완성 문서·숨겨진 문서의 연결도 보고합니다.
이 진단 때문에 기존 문서나 메뉴를 자동 수정하지 않습니다. CI에서는 해당 진단을 참고용으로 남깁니다.

## 검사와 미리보기

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
npm test
.venv/bin/python scripts/check_site.py
bundle exec jekyll build
.venv/bin/python scripts/check_build.py _site
bundle exec jekyll serve --host 127.0.0.1
```

브라우저에서 http://127.0.0.1:4000 을 엽니다. PR에서는 검사와 빌드만, main에서는 배포까지 실행합니다.
로컬 원본과 GUI를 CI에서 실행하지 않습니다. CI는 이미 생성해 커밋한 YAML/PDF로 빌드합니다.

## 실패와 복구

- 입력창 취소나 생성 실패 시 대기 중 기록 `.daily_record_pending.json`은 유지됩니다.
- 공개 PDF와 YAML은 임시 위치에서 준비·검증한 뒤 교체합니다. 처리 가능한 오류는 즉시 이전 쌍으로 되돌립니다.
- 강제 종료로 남은 `.cache/notes-publication/`은 다음 생성기 실행 시작 시 복구됩니다. **이 폴더를 먼저 지우지 마세요.**
- `.cache/ink/`만 삭제하면 잉크 계산 캐시를 안전하게 다시 만들 수 있습니다. 첫 실행은 오래 걸릴 수 있습니다.
- 계산 캐시는 PDF 내용, 계산 코드·설정, PyMuPDF/NumPy 버전과 기준 PDF가 바뀌면 자동 무효화됩니다.
- 갱신기는 동시 실행을 막습니다. 원본 PDF는 갱신 작업이 끝난 뒤 수정하세요.

2026-10-12 정리 전 전체 백업:
`/Users/persist/math-blog-backups/2026-10-12-before-cleanup/math-blog`

바깥의 `verification.json`에 원본 전체 파일 SHA-256 목록과 검증 결과가 있습니다.
복원할 때는 현재 폴더를 따로 보관하고 백업을 새 폴더로 복사해 확인하세요. 백업 위에서 직접 작업하지 마세요.
