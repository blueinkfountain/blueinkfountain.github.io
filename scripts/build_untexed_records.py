from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher
import hashlib
import re

import fitz
import numpy as np
import yaml


# =========================================================
# Paths
# =========================================================

ROOT = Path(__file__).resolve().parents[1]

UNTEXED = ROOT / "untexed"

OUTPUT = ROOT / "_data" / "untexed_records.yml"


# =========================================================
# Ink reference
#
# _ink_reference/
#   ink_100.pdf
#   grid_template.pdf
#
# ink_100.pdf:
#   이 한 페이지의 필기량을 정확히 100%로 정의
#
# grid_template.pdf:
#   빈 reMarkable 격자 페이지
# =========================================================

REFERENCE_DIR = ROOT / "_ink_reference"

INK_REFERENCE_PDF = (
    REFERENCE_DIR
    / "ink_100.pdf"
)

GRID_TEMPLATE_PDF = (
    REFERENCE_DIR
    / "grid_template.pdf"
)


# =========================================================
# Rendering / Ink parameters
# =========================================================

RENDER_SCALE = 2.0


# 템플릿보다 최소 이만큼 어두워져야
# 실제 필기 후보로 인정
TEMPLATE_DIFF_THRESHOLD = 20


# 너무 밝은 anti-aliasing이나
# 배경 변화는 필기로 세지 않음
MAX_INK_GRAY = 220


# reMarkable export 과정에서
# 페이지가 몇 pixel 정도 이동하는 경우 보정
MAX_ALIGNMENT_SHIFT = 3


# 기존 글씨 가장자리의 anti-aliasing 변화를
# 새로운 필기로 잘못 세지 않기 위한 tolerance
OLD_INK_TOLERANCE_RADIUS = 2


# Rename 추정은 보수적으로
RENAME_SIMILARITY_THRESHOLD = 0.80


_TEMPLATE_GRAY = None

_REFERENCE_INK_PIXELS = None


# =========================================================
# Path utilities
# =========================================================

def strip_pdf_suffixes(name):

    result = name

    while result.lower().endswith(".pdf"):

        result = result[:-4]

    return result


def display_path(relative_path):

    parts = relative_path.split("/")

    cleaned = []


    for index, part in enumerate(parts):

        if index == len(parts) - 1:

            # 파일명
            #
            # abc.pdf
            # abc.pdf.pdf
            #
            # 모두 abc로 표시
            part = strip_pdf_suffixes(
                part
            )

        else:

            # 폴더명의 번호 제거
            #
            # 3. Finite Group Theory
            # ->
            # Finite Group Theory
            part = re.sub(
                r"^\d+\.\s*",
                "",
                part
            )

        cleaned.append(
            part
        )


    return "/".join(
        cleaned
    )


def normalized_filename(relative_path):

    name = Path(
        relative_path
    ).name


    name = strip_pdf_suffixes(
        name
    )


    name = name.lower()


    name = re.sub(
        r"[\s_\-()]+",
        " ",
        name
    )


    return name.strip()


def top_subject(relative_path):

    parts = relative_path.split("/")

    if parts:

        return parts[0]

    return ""


# =========================================================
# PDF page rendering
# =========================================================

def render_page_gray(page):

    pix = page.get_pixmap(

        matrix=fitz.Matrix(
            RENDER_SCALE,
            RENDER_SCALE
        ),

        colorspace=fitz.csGRAY,

        alpha=False

    )


    return np.frombuffer(

        pix.samples,

        dtype=np.uint8

    ).reshape(

        pix.height,

        pix.width

    ).copy()


# =========================================================
# Resize grayscale template
# =========================================================

def resize_gray_nearest(
    gray,
    target_shape
):

    if gray.shape == target_shape:

        return gray


    target_h, target_w = (
        target_shape
    )

    source_h, source_w = (
        gray.shape
    )


    y_idx = np.linspace(

        0,

        source_h - 1,

        target_h

    ).astype(
        np.int64
    )


    x_idx = np.linspace(

        0,

        source_w - 1,

        target_w

    ).astype(
        np.int64
    )


    return gray[

        np.ix_(
            y_idx,
            x_idx
        )

    ]


# =========================================================
# Resize boolean mask
# =========================================================

def resize_mask_nearest(
    mask,
    target_shape
):

    if mask.shape == target_shape:

        return mask


    target_h, target_w = (
        target_shape
    )

    source_h, source_w = (
        mask.shape
    )


    y_idx = np.linspace(

        0,

        source_h - 1,

        target_h

    ).astype(
        np.int64
    )


    x_idx = np.linspace(

        0,

        source_w - 1,

        target_w

    ).astype(
        np.int64
    )


    return mask[

        np.ix_(
            y_idx,
            x_idx
        )

    ]


# =========================================================
# Load reference PDF first page
# =========================================================

def load_first_page_gray(
    pdf_path
):

    doc = fitz.open(
        pdf_path
    )


    try:

        if doc.page_count < 1:

            raise ValueError(

                f"No pages in reference PDF: "
                f"{pdf_path}"

            )


        return render_page_gray(

            doc.load_page(0)

        )


    finally:

        doc.close()


# =========================================================
# Handwriting mask
#
# 핵심:
#
# blank grid와 실제 page를 비교한다.
#
# template - actual page
#
# 실제 page 쪽이 충분히 어두워진 부분만
# handwriting으로 본다.
#
# 따라서 격자 자체는 자동으로 제거된다.
# =========================================================

def handwriting_mask_from_gray(
    gray
):

    if _TEMPLATE_GRAY is None:

        raise RuntimeError(

            "Ink calibration has not "
            "been initialized."

        )


    template = resize_gray_nearest(

        _TEMPLATE_GRAY,

        gray.shape

    )


    # uint8 subtraction overflow 방지
    darkness_gain = (

        template.astype(
            np.int16
        )

        -

        gray.astype(
            np.int16
        )

    )


    return (

        (
            darkness_gain
            >=
            TEMPLATE_DIFF_THRESHOLD
        )

        &

        (
            gray
            <
            MAX_INK_GRAY
        )

    )


def page_ink_mask(page):

    return handwriting_mask_from_gray(

        render_page_gray(
            page
        )

    )


# =========================================================
# Calibration
#
# 매번 ink_100.pdf를 직접 읽는다.
#
# 따라서 특정 pixel 값을 코드에 하드코딩하지 않는다.
#
# ink_100.pdf에서 검출된 필기량
# = 정확히 100%
# =========================================================

def initialize_ink_calibration():

    global _TEMPLATE_GRAY

    global _REFERENCE_INK_PIXELS


    if not INK_REFERENCE_PDF.exists():

        raise FileNotFoundError(

            f"Missing ink reference PDF:\n"
            f"{INK_REFERENCE_PDF}"

        )


    if not GRID_TEMPLATE_PDF.exists():

        raise FileNotFoundError(

            f"Missing grid template PDF:\n"
            f"{GRID_TEMPLATE_PDF}"

        )


    # 빈 격자
    _TEMPLATE_GRAY = (
        load_first_page_gray(
            GRID_TEMPLATE_PDF
        )
    )


    # 100% 필기 기준 페이지
    reference_gray = (
        load_first_page_gray(
            INK_REFERENCE_PDF
        )
    )


    reference_mask = (
        handwriting_mask_from_gray(
            reference_gray
        )
    )


    _REFERENCE_INK_PIXELS = int(

        np.count_nonzero(
            reference_mask
        )

    )


    if _REFERENCE_INK_PIXELS <= 0:

        raise RuntimeError(

            "Reference ink amount is zero. "
            "Check reference/template PDFs."

        )


    # 빈 격자가 필기로 잘못 잡히는지 검사
    blank_mask = (
        handwriting_mask_from_gray(
            _TEMPLATE_GRAY
        )
    )


    blank_pixels = int(

        np.count_nonzero(
            blank_mask
        )

    )


    print()

    print(
        "=" * 70
    )

    print(
        "Ink calibration"
    )

    print(
        "=" * 70
    )


    print(

        f"100% reference ink : "
        f"{_REFERENCE_INK_PIXELS:,} pixels"

    )


    print(

        f"Blank grid ink     : "
        f"{blank_pixels:,} pixels"

    )


    print(
        "=" * 70
    )

    print()


# =========================================================
# PDF visual hash
#
# metadata가 아니라 실제 렌더링 화면을 비교한다.
# =========================================================

def visual_pdf_hash(path):

    h = hashlib.sha256()


    doc = fitz.open(
        path
    )


    try:

        h.update(

            str(
                doc.page_count
            ).encode(
                "utf-8"
            )

        )


        for page_number in range(
            doc.page_count
        ):

            page = doc.load_page(
                page_number
            )


            pix = page.get_pixmap(

                matrix=fitz.Matrix(
                    RENDER_SCALE,
                    RENDER_SCALE
                ),

                alpha=False

            )


            h.update(

                str(
                    pix.width
                ).encode(
                    "utf-8"
                )

            )


            h.update(

                str(
                    pix.height
                ).encode(
                    "utf-8"
                )

            )


            h.update(
                pix.samples
            )


        return h.hexdigest()


    finally:

        doc.close()


# =========================================================
# Shift mask
# =========================================================

def shift_mask(
    mask,
    dx,
    dy
):

    height, width = (
        mask.shape
    )


    shifted = np.zeros_like(

        mask,

        dtype=bool

    )


    src_x1 = max(
        0,
        -dx
    )

    src_x2 = min(
        width,
        width - dx
    )


    src_y1 = max(
        0,
        -dy
    )

    src_y2 = min(
        height,
        height - dy
    )


    dst_x1 = max(
        0,
        dx
    )

    dst_x2 = min(
        width,
        width + dx
    )


    dst_y1 = max(
        0,
        dy
    )

    dst_y2 = min(
        height,
        height + dy
    )


    if (
        src_x1 >= src_x2
        or
        src_y1 >= src_y2
    ):

        return shifted


    shifted[

        dst_y1:dst_y2,

        dst_x1:dst_x2

    ] = mask[

        src_y1:src_y2,

        src_x1:src_x2

    ]


    return shifted


# =========================================================
# Old/New page alignment
#
# reMarkable 재-export 과정의
# ±몇 pixel 차이를 보정한다.
# =========================================================

def align_old_mask(
    old_mask,
    new_mask
):

    old_mask = (
        resize_mask_nearest(

            old_mask,

            new_mask.shape

        )
    )


    best = old_mask


    best_overlap = int(

        np.count_nonzero(

            old_mask
            &
            new_mask

        )

    )


    for dy in range(

        -MAX_ALIGNMENT_SHIFT,

        MAX_ALIGNMENT_SHIFT + 1

    ):


        for dx in range(

            -MAX_ALIGNMENT_SHIFT,

            MAX_ALIGNMENT_SHIFT + 1

        ):


            if (
                dx == 0
                and
                dy == 0
            ):

                continue


            candidate = shift_mask(

                old_mask,

                dx,

                dy

            )


            overlap = int(

                np.count_nonzero(

                    candidate
                    &
                    new_mask

                )

            )


            if overlap > best_overlap:

                best_overlap = overlap

                best = candidate


    return best


# =========================================================
# Existing ink tolerance
# =========================================================

def dilate_mask(
    mask,
    radius
):

    if radius <= 0:

        return mask


    result = mask.copy()


    for dy in range(

        -radius,

        radius + 1

    ):


        for dx in range(

            -radius,

            radius + 1

        ):


            if (
                dx == 0
                and
                dy == 0
            ):

                continue


            result |= shift_mask(

                mask,

                dx,

                dy

            )


    return result


# =========================================================
# Added file
#
# 새 파일 전체의 필기량 계산
# =========================================================

def count_total_ink_pixels(
    pdf_path
):

    total = 0


    doc = fitz.open(
        pdf_path
    )


    try:

        for page_number in range(
            doc.page_count
        ):


            page = doc.load_page(
                page_number
            )


            mask = page_ink_mask(
                page
            )


            total += int(

                np.count_nonzero(
                    mask
                )

            )


        return total


    finally:

        doc.close()


# =========================================================
# Modified file
#
# old -> new에서
# 새로 추가된 필기만 계산
# =========================================================

def count_added_ink_pixels(

    old_pdf_path,

    new_pdf_path

):

    old_doc = fitz.open(
        old_pdf_path
    )


    new_doc = fitz.open(
        new_pdf_path
    )


    try:

        total_added = 0


        common_pages = min(

            old_doc.page_count,

            new_doc.page_count

        )


        # -------------------------------------------------
        # 기존 페이지
        # -------------------------------------------------

        for page_number in range(
            common_pages
        ):


            old_mask = page_ink_mask(

                old_doc.load_page(
                    page_number
                )

            )


            new_mask = page_ink_mask(

                new_doc.load_page(
                    page_number
                )

            )


            # 위치 보정
            old_mask = align_old_mask(

                old_mask,

                new_mask

            )


            # 기존 글씨 가장자리 tolerance
            old_mask = dilate_mask(

                old_mask,

                OLD_INK_TOLERANCE_RADIUS

            )


            # new에는 있지만 old에는 없었던 ink
            added_mask = (

                new_mask

                &

                ~old_mask

            )


            total_added += int(

                np.count_nonzero(
                    added_mask
                )

            )


        # -------------------------------------------------
        # 파일 뒤쪽에 새 페이지가 추가된 경우
        #
        # 해당 페이지 전체 handwriting을
        # 그날 추가된 ink로 계산
        # -------------------------------------------------

        for page_number in range(

            common_pages,

            new_doc.page_count

        ):


            new_mask = page_ink_mask(

                new_doc.load_page(
                    page_number
                )

            )


            total_added += int(

                np.count_nonzero(
                    new_mask
                )

            )


        return total_added


    finally:

        old_doc.close()

        new_doc.close()


# =========================================================
# Ink %
#
# 기준 페이지 한 장 = 100%
#
# 3.14장 분량 = 314%
# =========================================================

def ink_percent(
    pixel_count
):

    if _REFERENCE_INK_PIXELS is None:

        raise RuntimeError(

            "Ink calibration has not "
            "been initialized."

        )


    return (

        pixel_count

        /

        _REFERENCE_INK_PIXELS

        *

        100.0

    )


def rounded_ink_percent(
    pixel_count
):

    return round(

        ink_percent(
            pixel_count
        ),

        1

    )


# =========================================================
# Snapshot
# =========================================================

def get_pdf_snapshot(
    date_dir
):

    snapshot = {}


    pdf_paths = sorted(

        path

        for path in date_dir.rglob("*")

        if (

            path.is_file()

            and

            path.suffix.lower()
            == ".pdf"

        )

    )


    for path in pdf_paths:


        relative_path = (

            path

            .relative_to(
                date_dir
            )

            .as_posix()

        )


        print(

            f"Hashing "
            f"[{date_dir.name}] "
            f"{relative_path}"

        )


        snapshot[
            relative_path
        ] = {

            "hash":
                visual_pdf_hash(
                    path
                ),

            "name":
                path.name

        }


    return snapshot


# =========================================================
# Moved / Renamed
#
# 오판을 방지하기 위해 보수적으로 판정
# =========================================================

def detect_moves(

    previous,

    current,

    deleted_candidates,

    added_candidates

):

    moved = []


    # =====================================================
    # STEP 1
    #
    # 같은 subject
    # + 같은 filename
    # + 각각 후보가 하나뿐
    #
    # 내용이 조금 수정돼도 move로 판정 가능
    # =====================================================

    old_by_identity = (
        defaultdict(list)
    )

    new_by_identity = (
        defaultdict(list)
    )


    for path in deleted_candidates:


        key = (

            top_subject(
                path
            ),

            normalized_filename(
                path
            )

        )


        old_by_identity[
            key
        ].append(
            path
        )


    for path in added_candidates:


        key = (

            top_subject(
                path
            ),

            normalized_filename(
                path
            )

        )


        new_by_identity[
            key
        ].append(
            path
        )


    common_keys = (

        set(
            old_by_identity
        )

        &

        set(
            new_by_identity
        )

    )


    for key in sorted(
        common_keys
    ):


        old_list = sorted(

            old_by_identity[
                key
            ]

        )


        new_list = sorted(

            new_by_identity[
                key
            ]

        )


        if (

            len(old_list) == 1

            and

            len(new_list) == 1

        ):


            old_path = (
                old_list[0]
            )


            new_path = (
                new_list[0]
            )


            moved.append({

                "from":
                    old_path,

                "to":
                    new_path

            })


            deleted_candidates.remove(
                old_path
            )


            added_candidates.remove(
                new_path
            )


    # =====================================================
    # STEP 2
    #
    # 동일 visual hash
    # + 동일 filename
    #
    # 단 후보가 각각 하나일 때만
    # =====================================================

    deleted_by_hash = (
        defaultdict(list)
    )

    added_by_hash = (
        defaultdict(list)
    )


    for path in deleted_candidates:


        deleted_by_hash[

            previous[path][
                "hash"
            ]

        ].append(
            path
        )


    for path in added_candidates:


        added_by_hash[

            current[path][
                "hash"
            ]

        ].append(
            path
        )


    common_hashes = (

        set(
            deleted_by_hash
        )

        &

        set(
            added_by_hash
        )

    )


    for file_hash in sorted(
        common_hashes
    ):


        old_by_name = (
            defaultdict(list)
        )


        new_by_name = (
            defaultdict(list)
        )


        for path in (
            deleted_by_hash[
                file_hash
            ]
        ):


            if path in deleted_candidates:


                old_by_name[

                    normalized_filename(
                        path
                    )

                ].append(
                    path
                )


        for path in (
            added_by_hash[
                file_hash
            ]
        ):


            if path in added_candidates:


                new_by_name[

                    normalized_filename(
                        path
                    )

                ].append(
                    path
                )


        same_names = (

            set(
                old_by_name
            )

            &

            set(
                new_by_name
            )

        )


        for name in sorted(
            same_names
        ):


            old_list = sorted(

                old_by_name[
                    name
                ]

            )


            new_list = sorted(

                new_by_name[
                    name
                ]

            )


            # 같은 hash / 같은 이름이 여러 개면
            # 억지로 pairing하지 않는다.
            if (

                len(old_list) != 1

                or

                len(new_list) != 1

            ):

                continue


            old_path = (
                old_list[0]
            )


            new_path = (
                new_list[0]
            )


            moved.append({

                "from":
                    old_path,

                "to":
                    new_path

            })


            deleted_candidates.remove(
                old_path
            )


            added_candidates.remove(
                new_path
            )


    # =====================================================
    # STEP 3
    #
    # 동일 hash 그룹에
    # old/new 후보가 정확히 하나씩이고
    #
    # 같은 subject
    # + 이름이 충분히 비슷할 때만
    #
    # rename으로 판단
    # =====================================================

    deleted_by_hash = (
        defaultdict(list)
    )

    added_by_hash = (
        defaultdict(list)
    )


    for path in deleted_candidates:


        deleted_by_hash[

            previous[path][
                "hash"
            ]

        ].append(
            path
        )


    for path in added_candidates:


        added_by_hash[

            current[path][
                "hash"
            ]

        ].append(
            path
        )


    common_hashes = (

        set(
            deleted_by_hash
        )

        &

        set(
            added_by_hash
        )

    )


    for file_hash in sorted(
        common_hashes
    ):


        old_paths = [

            path

            for path in
            deleted_by_hash[
                file_hash
            ]

            if path
            in deleted_candidates

        ]


        new_paths = [

            path

            for path in
            added_by_hash[
                file_hash
            ]

            if path
            in added_candidates

        ]


        # ambiguous hash group은
        # rename으로 추정하지 않는다.
        if (

            len(old_paths) != 1

            or

            len(new_paths) != 1

        ):

            continue


        old_path = (
            old_paths[0]
        )


        new_path = (
            new_paths[0]
        )


        if (

            top_subject(
                old_path
            )

            !=

            top_subject(
                new_path
            )

        ):

            continue


        similarity = (
            SequenceMatcher(

                None,

                normalized_filename(
                    old_path
                ),

                normalized_filename(
                    new_path
                )

            ).ratio()
        )


        if (

            similarity
            <
            RENAME_SIMILARITY_THRESHOLD

        ):

            continue


        moved.append({

            "from":
                old_path,

            "to":
                new_path

        })


        deleted_candidates.remove(
            old_path
        )


        added_candidates.remove(
            new_path
        )


    return moved


# =========================================================
# Main
# =========================================================

def main():


    # =====================================================
    # 100% reference calibration
    # =====================================================

    initialize_ink_calibration()


    # =====================================================
    # 날짜 폴더
    # =====================================================

    date_dirs = sorted(

        [

            path

            for path in UNTEXED.iterdir()

            if (

                path.is_dir()

                and

                path.name.isdigit()

                and

                len(path.name) == 6

            )

        ],

        key=lambda path:
            path.name

    )


    if not date_dirs:

        print(
            "No dated folders found."
        )

        return


    print(
        "Found versions:"
    )

    print()


    for date_dir in date_dirs:

        print(

            f"  {date_dir.name}"

        )


    print()


    # =====================================================
    # Snapshot 생성
    # =====================================================

    snapshots = {}


    for date_dir in date_dirs:


        print(
            "=" * 70
        )


        print(

            f"Scanning "
            f"{date_dir.name}"

        )


        print(
            "=" * 70
        )

        print()


        snapshots[
            date_dir.name
        ] = get_pdf_snapshot(
            date_dir
        )


        print()


    # =====================================================
    # Record 생성
    # =====================================================

    records = {}


    for index, date_dir in enumerate(
        date_dirs
    ):


        date = (
            date_dir.name
        )


        current = snapshots[
            date
        ]


        # =================================================
        # 첫 snapshot
        #
        # 이전 상태가 없으므로
        # "그날 쓴 양"을 계산할 수 없다.
        # =================================================

        if index == 0:


            records[
                date
            ] = {

                "baseline":
                    True,

                "total_ink_percent":
                    None,

                "added":
                    [],

                "modified":
                    [],

                "moved_renamed":
                    [],

                "deleted":
                    []

            }


            continue


        # =================================================
        # Previous snapshot
        # =================================================

        previous_dir = (
            date_dirs[
                index - 1
            ]
        )


        previous_date = (
            previous_dir.name
        )


        previous = snapshots[
            previous_date
        ]


        previous_paths = set(
            previous
        )


        current_paths = set(
            current
        )


        common_paths = (

            previous_paths

            &

            current_paths

        )


        # =================================================
        # Modified candidate
        # =================================================

        modified_raw = sorted(

            path

            for path in common_paths

            if (

                previous[path][
                    "hash"
                ]

                !=

                current[path][
                    "hash"
                ]

            )

        )


        # =================================================
        # Added / Deleted candidates
        # =================================================

        added_candidates = set(

            current_paths

            -

            previous_paths

        )


        deleted_candidates = set(

            previous_paths

            -

            current_paths

        )


        # =================================================
        # Moved / Renamed
        # =================================================

        moved_raw = detect_moves(

            previous,

            current,

            deleted_candidates,

            added_candidates

        )


        # =================================================
        # 이 날짜에 새로 추가된 전체 ink pixel
        #
        # 마지막에 이것 하나로
        # Record total을 계산한다.
        # =================================================

        total_added_ink_pixels = 0


        # =================================================
        # Added
        # =================================================

        added = []


        for path in sorted(
            added_candidates
        ):


            current_pdf = (

                date_dir

                /

                Path(path)

            )


            pixels = (
                count_total_ink_pixels(
                    current_pdf
                )
            )


            total_added_ink_pixels += (
                pixels
            )


            added.append({

                "path":
                    display_path(
                        path
                    ),

                "ink_added_percent":
                    rounded_ink_percent(
                        pixels
                    )

            })


        # =================================================
        # Modified
        # =================================================

        modified = []


        for path in modified_raw:


            old_pdf = (

                previous_dir

                /

                Path(path)

            )


            new_pdf = (

                date_dir

                /

                Path(path)

            )


            pixels = (
                count_added_ink_pixels(

                    old_pdf,

                    new_pdf

                )
            )


            total_added_ink_pixels += (
                pixels
            )


            modified.append({

                "path":
                    display_path(
                        path
                    ),

                "ink_added_percent":
                    rounded_ink_percent(
                        pixels
                    )

            })


        # =================================================
        # Removed
        #
        # 삭제는 필기량 합계에 포함하지 않는다.
        # =================================================

        deleted = [

            display_path(
                path
            )

            for path in sorted(
                deleted_candidates
            )

        ]


        # =================================================
        # Moved / Renamed
        #
        # 순수 이동:
        #   ink = 0
        #
        # 이동하면서 내용 수정:
        #   새로 추가된 ink만 합산
        # =================================================

        moved_renamed = []


        for item in sorted(

            moved_raw,

            key=lambda value: (

                value["from"],

                value["to"]

            )

        ):


            old_path = item[
                "from"
            ]


            new_path = item[
                "to"
            ]


            move_item = {

                "from":
                    display_path(
                        old_path
                    ),

                "to":
                    display_path(
                        new_path
                    ),

                "ink_added_percent":
                    0.0

            }


            # 이동하면서 실제 내용도 바뀜
            if (

                previous[
                    old_path
                ]["hash"]

                !=

                current[
                    new_path
                ]["hash"]

            ):


                old_pdf = (

                    previous_dir

                    /

                    Path(
                        old_path
                    )

                )


                new_pdf = (

                    date_dir

                    /

                    Path(
                        new_path
                    )

                )


                pixels = (
                    count_added_ink_pixels(

                        old_pdf,

                        new_pdf

                    )
                )


                total_added_ink_pixels += (
                    pixels
                )


                move_item[
                    "ink_added_percent"
                ] = (
                    rounded_ink_percent(
                        pixels
                    )
                )


            moved_renamed.append(
                move_item
            )


        # =================================================
        # Record
        # =================================================

        records[
            date
        ] = {

            "baseline":
                False,

            "total_ink_percent":
                rounded_ink_percent(

                    total_added_ink_pixels

                ),

            "added":
                added,

            "modified":
                modified,

            "moved_renamed":
                moved_renamed,

            "deleted":
                deleted

        }


    # =====================================================
    # YAML
    # =====================================================

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

            width=180

        )


    # =====================================================
    # Terminal summary
    # =====================================================

    print()

    print(
        "=" * 70
    )

    print(
        "Record summary"
    )

    print(
        "=" * 70
    )

    print()


    for date, record in records.items():


        print(
            date
        )


        if record[
            "baseline"
        ]:


            print(
                "  Baseline snapshot"
            )


        else:


            print(

                f"  Total ink     : "
                f"+{record['total_ink_percent']:.1f}%"

            )


            print(

                f"  Added         : "
                f"{len(record['added'])}"

            )


            print(

                f"  Modified      : "
                f"{len(record['modified'])}"

            )


            print(

                f"  Moved/Renamed : "
                f"{len(record['moved_renamed'])}"

            )


            print(

                f"  Removed       : "
                f"{len(record['deleted'])}"

            )


        print()


    print(

        f"Generated: "
        f"{OUTPUT}"

    )


if __name__ == "__main__":

    main()