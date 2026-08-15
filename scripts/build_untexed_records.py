from pathlib import Path, PurePosixPath
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
# Settings
# =========================================================

RENDER_SCALE = 2.0

TEMPLATE_DIFF_THRESHOLD = 20

MAX_INK_GRAY = 220

MAX_ALIGNMENT_SHIFT = 3

OLD_INK_TOLERANCE_RADIUS = 2

RENAME_SIMILARITY_THRESHOLD = 0.80


_TEMPLATE_GRAY = None

_REFERENCE_INK_PIXELS = None


# =========================================================
# Path helpers
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

            part = strip_pdf_suffixes(
                part
            )

        else:

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

    if len(parts) <= 1:
        return "General"

    return parts[0]


def folder_key(relative_path):

    parent = (
        PurePosixPath(relative_path)
        .parent
        .as_posix()
    )

    if parent == ".":
        return "General"

    return parent


def subject_key(relative_path):

    parts = relative_path.split("/")

    if len(parts) <= 1:
        return "General"

    return parts[0]


# =========================================================
# Rendering
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


def resize_nearest(
    array,
    target_shape
):

    if array.shape == target_shape:
        return array


    target_h, target_w = target_shape

    source_h, source_w = array.shape


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


    return array[

        np.ix_(
            y_idx,
            x_idx
        )

    ]


def load_first_page_gray(
    pdf_path
):

    doc = fitz.open(
        pdf_path
    )


    try:

        if doc.page_count < 1:

            raise RuntimeError(

                f"No pages in PDF: "
                f"{pdf_path}"

            )


        return render_page_gray(

            doc.load_page(0)

        )


    finally:

        doc.close()


# =========================================================
# Handwriting detection
#
# blank grid와 비교해서
# grid보다 실제로 어두워진 부분만 handwriting으로 판정
# =========================================================

def handwriting_mask_from_gray(
    gray
):

    if _TEMPLATE_GRAY is None:

        raise RuntimeError(
            "Ink calibration is not initialized."
        )


    template = resize_nearest(

        _TEMPLATE_GRAY,

        gray.shape

    )


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
# Ink calibration
#
# ink_100.pdf = 정확히 100%
# =========================================================

def initialize_ink_calibration():

    global _TEMPLATE_GRAY
    global _REFERENCE_INK_PIXELS


    if not INK_REFERENCE_PDF.exists():

        raise FileNotFoundError(

            f"Missing reference file:\n"
            f"{INK_REFERENCE_PDF}"

        )


    if not GRID_TEMPLATE_PDF.exists():

        raise FileNotFoundError(

            f"Missing template file:\n"
            f"{GRID_TEMPLATE_PDF}"

        )


    _TEMPLATE_GRAY = (

        load_first_page_gray(
            GRID_TEMPLATE_PDF
        )

    )


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
            "Reference ink amount is zero."
        )


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
    print("=" * 70)
    print("Ink calibration")
    print("=" * 70)

    print(

        f"100% reference ink : "
        f"{_REFERENCE_INK_PIXELS:,} pixels"

    )

    print(

        f"Blank grid ink     : "
        f"{blank_pixels:,} pixels"

    )

    print("=" * 70)
    print()


# =========================================================
# Visual PDF hash
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
# Mask utilities
# =========================================================

def shift_mask(
    mask,
    dx,
    dy
):

    height, width = mask.shape


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


def align_old_mask(
    old_mask,
    new_mask
):

    old_mask = resize_nearest(

        old_mask,

        new_mask.shape

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


            if dx == 0 and dy == 0:
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


            if dx == 0 and dy == 0:
                continue


            result |= shift_mask(

                mask,

                dx,

                dy

            )


    return result


# =========================================================
# Ink calculations
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


            mask = page_ink_mask(

                doc.load_page(
                    page_number
                )

            )


            total += int(

                np.count_nonzero(
                    mask
                )

            )


        return total


    finally:

        doc.close()


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


        # Existing pages

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


            old_mask = align_old_mask(

                old_mask,

                new_mask

            )


            old_mask = dilate_mask(

                old_mask,

                OLD_INK_TOLERANCE_RADIUS

            )


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


        # Newly appended pages

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


def ink_percent(pixel_count):

    if _REFERENCE_INK_PIXELS is None:

        raise RuntimeError(
            "Ink calibration is not initialized."
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
            path.suffix.lower() == ".pdf"
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
# Moved / Renamed detection
# =========================================================

def detect_moves(

    previous,

    current,

    deleted_candidates,

    added_candidates

):

    moved = []


    # -----------------------------------------------------
    # STEP 1
    # Same subject + same filename
    # -----------------------------------------------------

    old_by_identity = defaultdict(
        list
    )

    new_by_identity = defaultdict(
        list
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
            old_by_identity[key]
        )

        new_list = sorted(
            new_by_identity[key]
        )


        if (
            len(old_list) == 1
            and
            len(new_list) == 1
        ):


            old_path = old_list[0]

            new_path = new_list[0]


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


    # -----------------------------------------------------
    # STEP 2
    # Same visual hash + similar filename
    # -----------------------------------------------------

    deleted_by_hash = defaultdict(
        list
    )

    added_by_hash = defaultdict(
        list
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


        # ambiguous group은 pairing 안 함

        if (
            len(old_paths) != 1
            or
            len(new_paths) != 1
        ):

            continue


        old_path = old_paths[0]

        new_path = new_paths[0]


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


        old_name = normalized_filename(
            old_path
        )

        new_name = normalized_filename(
            new_path
        )


        similarity = SequenceMatcher(

            None,

            old_name,

            new_name

        ).ratio()


        if (
            old_name != new_name
            and
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

    initialize_ink_calibration()


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
    # Snapshots
    # =====================================================

    snapshots = {}


    for date_dir in date_dirs:


        print(
            "=" * 70
        )

        print(
            f"Scanning {date_dir.name}"
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
    # Records
    # =====================================================

    records = {}


    for index, date_dir in enumerate(
        date_dirs
    ):


        date = date_dir.name

        current = snapshots[
            date
        ]


        # -------------------------------------------------
        # Baseline
        # -------------------------------------------------

        if index == 0:


            records[
                date
            ] = {

                "baseline":
                    True,

                "total_ink_percent":
                    None,

                "subject_ink_percent":
                    {},

                "folder_ink_percent":
                    {},

                "file_ink_percent":
                    {},

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


        previous_dir = (
            date_dirs[
                index - 1
            ]
        )


        previous = snapshots[
            previous_dir.name
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


        moved_raw = detect_moves(

            previous,

            current,

            deleted_candidates,

            added_candidates

        )


        # =================================================
        # Ink statistics
        #
        # raw pixels로 먼저 저장한 뒤,
        # 마지막에 전부 %로 환산한다.
        # =================================================

        total_added_ink_pixels = 0


        file_ink_pixels = defaultdict(
            int
        )

        folder_ink_pixels = defaultdict(
            int
        )

        subject_ink_pixels = defaultdict(
            int
        )


        def register_ink(
            relative_path,
            pixels
        ):

            nonlocal total_added_ink_pixels


            total_added_ink_pixels += (
                pixels
            )


            file_ink_pixels[
                relative_path
            ] += pixels


            folder_ink_pixels[
                folder_key(
                    relative_path
                )
            ] += pixels


            subject_ink_pixels[
                subject_key(
                    relative_path
                )
            ] += pixels


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


            pixels = count_total_ink_pixels(
                current_pdf
            )


            register_ink(
                path,
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


            pixels = count_added_ink_pixels(

                old_pdf,

                new_pdf

            )


            register_ink(
                path,
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


                pixels = count_added_ink_pixels(

                    old_pdf,

                    new_pdf

                )


                register_ink(
                    new_path,
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
        # Convert hierarchy statistics to percentage
        # =================================================

        file_ink_percent = {

            path:
                rounded_ink_percent(
                    pixels
                )

            for path, pixels
            in sorted(
                file_ink_pixels.items()
            )

        }


        folder_ink_percent = {

            folder:
                rounded_ink_percent(
                    pixels
                )

            for folder, pixels
            in sorted(
                folder_ink_pixels.items()
            )

        }


        subject_ink_percent = {

            subject:
                rounded_ink_percent(
                    pixels
                )

            for subject, pixels
            in sorted(
                subject_ink_pixels.items()
            )

        }


        # =================================================
        # Final Record
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

            "subject_ink_percent":
                subject_ink_percent,

            "folder_ink_percent":
                folder_ink_percent,

            "file_ink_percent":
                file_ink_percent,

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
    # Summary
    # =====================================================

    print()
    print("=" * 70)
    print("Record summary")
    print("=" * 70)
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


            if record[
                "subject_ink_percent"
            ]:


                print(
                    "  Subjects:"
                )


                for subject, value in (
                    record[
                        "subject_ink_percent"
                    ].items()
                ):


                    print(

                        f"    {subject:<24} "
                        f"+{value:.1f}%"

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