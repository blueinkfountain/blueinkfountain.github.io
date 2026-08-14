from pathlib import Path
import hashlib
import yaml
import fitz  # PyMuPDF


# =========================================================
# 경로 설정
# =========================================================

ROOT = Path(__file__).resolve().parents[1]

UNTEXED = ROOT / "untexed"

OUTPUT = ROOT / "_data" / "untexed_records.yml"


# =========================================================
# PDF의 "보이는 내용"을 hash
#
# PDF 파일 자체의 bytes를 비교하지 않는다.
#
# 각 페이지를 실제 이미지로 렌더링한 뒤
# 그 픽셀 데이터를 hash한다.
#
# 따라서:
#
# - PDF 생성일 변경
# - 수정일 변경
# - Producer 변경
# - 내부 object 번호 변경
# - 압축 방식 변경
#
# 등은 무시한다.
#
# 반면 실제 필기 내용이 바뀌면 hash가 달라진다.
# =========================================================

def visual_pdf_hash(path):
    h = hashlib.sha256()

    try:
        document = fitz.open(path)

        # 페이지 수 자체도 hash에 포함
        h.update(str(document.page_count).encode("utf-8"))

        for page_number in range(document.page_count):

            page = document.load_page(page_number)

            # 2.0 = 약 144 DPI
            #
            # 필기나 작은 수식 변화까지 잡기에 충분하면서
            # 지나치게 느리지 않은 수준
            matrix = fitz.Matrix(2.0, 2.0)

            pixmap = page.get_pixmap(
                matrix=matrix,
                alpha=False
            )

            # 페이지 크기도 포함
            h.update(str(pixmap.width).encode("utf-8"))
            h.update(str(pixmap.height).encode("utf-8"))

            # 실제 픽셀 데이터
            h.update(pixmap.samples)

        document.close()

        return h.hexdigest()

    except Exception as e:

        print(f"[ERROR] Failed to read PDF: {path}")
        print(e)

        raise


# =========================================================
# 특정 날짜 폴더의 PDF snapshot 생성
#
# 예:
#
# 260813/
#   Algebra/
#     1. Linear Algebra/
#       vector.pdf
#
# ↓
#
# Algebra/1. Linear Algebra/vector.pdf
# =========================================================

def get_pdf_snapshot(date_dir):

    snapshot = {}

    for path in sorted(date_dir.rglob("*")):

        if (
            path.is_file()
            and path.suffix.lower() == ".pdf"
        ):

            relative_path = path.relative_to(date_dir).as_posix()

            print(
                f"Hashing [{date_dir.name}] "
                f"{relative_path}"
            )

            snapshot[relative_path] = {
                "hash": visual_pdf_hash(path),
                "name": path.name,
            }

    return snapshot


# =========================================================
# 날짜 폴더 탐색
#
# YYMMDD 형식의 숫자 폴더만 대상으로 함
# =========================================================

date_dirs = sorted(
    [
        path
        for path in UNTEXED.iterdir()

        if (
            path.is_dir()
            and path.name.isdigit()
            and len(path.name) == 6
        )
    ],
    key=lambda path: path.name
)


if not date_dirs:

    print("No dated folders found.")

    raise SystemExit(0)


print()
print("Found versions:")
print()

for date_dir in date_dirs:
    print(f"  {date_dir.name}")

print()


# =========================================================
# 모든 날짜 snapshot 생성
# =========================================================

snapshots = {}


for date_dir in date_dirs:

    print()
    print("=" * 60)
    print(f"Scanning {date_dir.name}")
    print("=" * 60)
    print()

    snapshots[date_dir.name] = get_pdf_snapshot(date_dir)


# =========================================================
# 날짜별 변경 내역 계산
# =========================================================

records = {}


for index, date_dir in enumerate(date_dirs):

    date = date_dir.name

    current = snapshots[date]


    # -----------------------------------------------------
    # 최초 날짜
    #
    # 비교 대상이 없으므로 모든 파일을 Added로 처리
    # -----------------------------------------------------

    if index == 0:

        records[date] = {
            "added": sorted(current.keys()),
            "modified": [],
            "deleted": [],
        }

        continue


    # -----------------------------------------------------
    # 직전 날짜
    # -----------------------------------------------------

    previous_date = date_dirs[index - 1].name

    previous = snapshots[previous_date]


    current_paths = set(current.keys())

    previous_paths = set(previous.keys())


    # -----------------------------------------------------
    # Added
    #
    # 현재 날짜에만 존재
    # -----------------------------------------------------

    added = sorted(
        current_paths - previous_paths
    )


    # -----------------------------------------------------
    # Removed
    #
    # 이전 날짜에만 존재
    # -----------------------------------------------------

    deleted = sorted(
        previous_paths - current_paths
    )


    # -----------------------------------------------------
    # Modified
    #
    # 파일의 상대경로는 동일하지만
    # 렌더링된 페이지 내용이 달라짐
    # -----------------------------------------------------

    common_paths = (
        current_paths
        & previous_paths
    )


    modified = sorted(

        path

        for path in common_paths

        if (
            current[path]["hash"]
            != previous[path]["hash"]
        )
    )


    records[date] = {
        "added": added,
        "modified": modified,
        "deleted": deleted,
    }


# =========================================================
# YAML 저장
# =========================================================

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)


with OUTPUT.open(
    "w",
    encoding="utf-8"
) as file:

    yaml.safe_dump(
        records,
        file,
        allow_unicode=True,
        sort_keys=False,
    )


# =========================================================
# 결과 출력
# =========================================================

print()
print("=" * 60)
print("Record summary")
print("=" * 60)
print()


for date in records:

    record = records[date]

    print(date)

    print(
        f"  Added    : {len(record['added'])}"
    )

    print(
        f"  Modified : {len(record['modified'])}"
    )

    print(
        f"  Removed  : {len(record['deleted'])}"
    )

    print()


print(
    f"Generated: {OUTPUT}"
)