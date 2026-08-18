from pathlib import Path, PurePosixPath
from collections import defaultdict
from difflib import SequenceMatcher
from urllib.parse import quote
from datetime import datetime
import hashlib
import math
import re
import shutil

import fitz
import numpy as np
import yaml


# =========================================================
# Paths
# =========================================================

ROOT = Path(__file__).resolve().parents[1]

# Local-only dated snapshots:
# untexed/260807/...
# untexed/260809/...
# ...
SNAPSHOT_ROOT = ROOT / "untexed"

# Only the newest snapshot is mirrored here and committed.
# GitHub Pages serves PDFs from this directory.
PUBLISHED_ROOT = ROOT / "untexed-current"

# This YAML is committed and contains all historical
# file lists, Records, and ink statistics.
OUTPUT = ROOT / "_data" / "untexed_records.yml"

REFERENCE_DIR = ROOT / "_ink_reference"
INK_REFERENCE_PDF = REFERENCE_DIR / "ink_100.pdf"
GRID_TEMPLATE_PDF = REFERENCE_DIR / "grid_template.pdf"


# =========================================================
# Ink / rendering settings
# =========================================================

RENDER_SCALE = 2.0
TEMPLATE_DIFF_THRESHOLD = 20
MAX_INK_GRAY = 220

# The exported page can shift its blank grid by a few raster pixels even when
# no handwriting changed.  Align the reference grid before subtracting it so
# grid jitter is not mistaken for newly written ink.
TEMPLATE_ALIGNMENT_SHIFT = 4
TEMPLATE_ALIGNMENT_SAMPLE_STEP = 4
TEMPLATE_ALIGNMENT_DIFF_CLIP = 40

# Old/new PDF exports can move or very slightly rescale a rendered page even
# when the handwriting itself did not change.  Registration therefore uses a
# cheap coarse search over a much wider translation window plus a few nearby
# uniform scales, then refines only around the best candidate at full size.
MAX_ALIGNMENT_SHIFT = 8
GLOBAL_ALIGNMENT_MAX_SHIFT = 48
GLOBAL_ALIGNMENT_COARSE_FACTOR = 6
GLOBAL_ALIGNMENT_REFINE_RADIUS = 5
GLOBAL_ALIGNMENT_SCALES = (0.97, 0.985, 1.0, 1.015, 1.03)
OLD_INK_TOLERANCE_RADIUS = 2

# A PDF app may silently re-export a note and slightly change anti-aliasing,
# stroke thickness, or grid rasterization.  Before calling such a file
# "Modified", compare the *structure* of the two ink masks with a wider
# tolerance.  Two masks that mutually cover one another this well are treated
# as the same handwriting.
REEXPORT_TOLERANCE_RADIUS = 8
REEXPORT_STRONG_COVERAGE = 0.995
REEXPORT_NORMAL_COVERAGE = 0.985
REEXPORT_STRONG_MAX_INK_DELTA = 0.08
REEXPORT_NORMAL_MAX_INK_DELTA = 0.02

# Fallback for pathological re-exports where almost the whole page appears to
# move at once.  Genuine additions are directional (new ink without a matching
# amount of vanished old ink); a re-export usually creates large *balanced*
# apparent added/removed ink while the coarse page structure and total ink stay
# nearly unchanged.
REEXPORT_BALANCED_COARSE_SIMILARITY = 0.90
REEXPORT_BALANCED_MIN_CHURN = 0.10
REEXPORT_BALANCED_MIN_SYMMETRY = 0.72
REEXPORT_BALANCED_MAX_INK_DELTA = 0.08

RENAME_SIMILARITY_THRESHOLD = 0.80

# Page-sequence alignment.  A page inserted or deleted in the middle of a PDF
# must not shift every later page comparison by one.  Each page gets a coarse
# handwriting signature, and a sequence alignment chooses the most plausible
# old/new page correspondence before ink differences are measured.
PAGE_SIGNATURE_ROWS = 32
PAGE_SIGNATURE_COLS = 24
PAGE_MATCH_BASELINE = 0.40
PAGE_GAP_PENALTY = -0.18
PAGE_MIN_REPORTED_MATCH = 0.18

# Keep the newest N snapshot folders recalculable.
# One immediately preceding snapshot is kept as a comparison anchor.
# Older records are frozen in _data/untexed_records.yml forever.
ROLLING_SNAPSHOTS = 3

# YAML folder-tree schema.
# Version 2 stores real recursive folders.
# Version 3 restores top-level PDFs under a special ``Others`` section.
TREE_SCHEMA_VERSION = 3

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


def strip_numeric_prefix(name):
    return re.sub(r"^\d+\.\s*", "", name)


def display_path(relative_path):
    parts = relative_path.split("/")
    cleaned = []

    for index, part in enumerate(parts):
        if index == len(parts) - 1:
            part = strip_pdf_suffixes(part)
        else:
            part = strip_numeric_prefix(part)
        cleaned.append(part)

    return "/".join(cleaned)


def display_folder(raw_folder):
    if raw_folder in {"General", "Others"}:
        return "Others"
    return " / ".join(raw_folder.split("/"))


def normalized_filename(relative_path):
    name = Path(relative_path).name
    name = strip_pdf_suffixes(name).lower()
    name = re.sub(r"[\s_\-()]+", " ", name)
    return name.strip()


def subject_key(relative_path):
    parts = relative_path.split("/")
    if len(parts) <= 1:
        return "Others"
    return parts[0]


def subject_sort_key(subject):
    """Keep the synthetic top-level-PDF section at the very bottom."""
    return (subject == "Others", subject.lower())


def top_subject(relative_path):
    return subject_key(relative_path)


def folder_key(relative_path):
    parent = PurePosixPath(relative_path).parent.as_posix()
    if parent == ".":
        return "Others"
    return parent


def folder_ancestor_keys(relative_path):
    """
    Return every real folder ancestor below the subject level.

    Example:
        Analysis/Real Analysis/Sequences/a.pdf
        -> [
             "Analysis/Real Analysis",
             "Analysis/Real Analysis/Sequences",
           ]

    The first component is the subject, so it is intentionally not
    repeated as a folder subtotal. Subject ink is tracked separately.
    """
    parts = list(PurePosixPath(relative_path).parts[:-1])

    if len(parts) <= 1:
        return []

    return [
        "/".join(parts[:depth])
        for depth in range(2, len(parts) + 1)
    ]


def published_url(relative_path):
    return "/untexed-current/" + quote(relative_path, safe="/")


def is_note_pdf(date_dir, path):
    """
    Treat every PDF inside a dated snapshot as a handwritten note.

    PDFs directly under the dated folder are no longer ignored;
    they are grouped into the synthetic ``Others`` section.

    Examples:
        untexed/260816/file.pdf              -> Others
        untexed/260816/Algebra/file.pdf      -> Algebra
        untexed/260816/Algebra/1. LA/a.pdf   -> Algebra / 1. LA
    """
    return (
        path.is_file()
        and path.suffix.lower() == ".pdf"
    )


# =========================================================
# PDF rendering
# =========================================================

def render_page_gray(page):
    pix = page.get_pixmap(
        matrix=fitz.Matrix(RENDER_SCALE, RENDER_SCALE),
        colorspace=fitz.csGRAY,
        alpha=False,
    )

    return np.frombuffer(
        pix.samples,
        dtype=np.uint8,
    ).reshape(
        pix.height,
        pix.width,
    ).copy()


def resize_nearest(array, target_shape):
    if array.shape == target_shape:
        return array

    target_h, target_w = target_shape
    source_h, source_w = array.shape

    y_idx = np.linspace(
        0,
        source_h - 1,
        target_h,
    ).astype(np.int64)

    x_idx = np.linspace(
        0,
        source_w - 1,
        target_w,
    ).astype(np.int64)

    return array[np.ix_(y_idx, x_idx)]


def load_first_page_gray(pdf_path):
    doc = fitz.open(pdf_path)

    try:
        if doc.page_count < 1:
            raise RuntimeError(f"No pages in PDF: {pdf_path}")

        return render_page_gray(doc.load_page(0))

    finally:
        doc.close()


def shift_gray(array, dx, dy, fill=255):
    """Shift a grayscale image without wrap-around."""
    height, width = array.shape

    shifted = np.full_like(
        array,
        fill,
    )

    src_x1 = max(0, -dx)
    src_x2 = min(width, width - dx)
    src_y1 = max(0, -dy)
    src_y2 = min(height, height - dy)

    dst_x1 = max(0, dx)
    dst_x2 = min(width, width + dx)
    dst_y1 = max(0, dy)
    dst_y2 = min(height, height + dy)

    if (
        src_x1 >= src_x2
        or src_y1 >= src_y2
    ):
        return shifted

    shifted[
        dst_y1:dst_y2,
        dst_x1:dst_x2,
    ] = array[
        src_y1:src_y2,
        src_x1:src_x2,
    ]

    return shifted


def template_alignment_score(template, gray, dx, dy):
    """Coarse robust score for shifting ``template`` by (dx, dy)."""
    height, width = gray.shape

    src_x1 = max(0, -dx)
    src_x2 = min(width, width - dx)
    src_y1 = max(0, -dy)
    src_y2 = min(height, height - dy)

    dst_x1 = max(0, dx)
    dst_x2 = min(width, width + dx)
    dst_y1 = max(0, dy)
    dst_y2 = min(height, height + dy)

    if (
        src_x1 >= src_x2
        or src_y1 >= src_y2
    ):
        return float("inf")

    step = TEMPLATE_ALIGNMENT_SAMPLE_STEP

    template_sample = template[
        src_y1:src_y2:step,
        src_x1:src_x2:step,
    ].astype(np.int16)

    gray_sample = gray[
        dst_y1:dst_y2:step,
        dst_x1:dst_x2:step,
    ].astype(np.int16)

    difference = np.abs(
        template_sample - gray_sample
    )

    # Handwriting should not dominate the background-grid registration.
    difference = np.minimum(
        difference,
        TEMPLATE_ALIGNMENT_DIFF_CLIP,
    )

    return float(
        difference.mean()
    )


def align_template_gray(template, gray):
    """
    Align the blank-grid template to one rendered page.

    This fixes the common case where a PDF app silently re-exports the same
    note with the background shifted by a few raster pixels.  Without this
    step, parts of the grid itself can be counted as handwriting.
    """
    best_dx = 0
    best_dy = 0
    best_score = template_alignment_score(
        template,
        gray,
        0,
        0,
    )

    for dy in range(
        -TEMPLATE_ALIGNMENT_SHIFT,
        TEMPLATE_ALIGNMENT_SHIFT + 1,
    ):
        for dx in range(
            -TEMPLATE_ALIGNMENT_SHIFT,
            TEMPLATE_ALIGNMENT_SHIFT + 1,
        ):
            if dx == 0 and dy == 0:
                continue

            score = template_alignment_score(
                template,
                gray,
                dx,
                dy,
            )

            if score < best_score:
                best_score = score
                best_dx = dx
                best_dy = dy

    if best_dx == 0 and best_dy == 0:
        return template

    return shift_gray(
        template,
        best_dx,
        best_dy,
    )


# =========================================================
# Handwriting detection
#
# The blank grid PDF is the background template.
# Pixels sufficiently darker than the template are treated
# as handwriting.
# =========================================================

def handwriting_mask_from_gray(gray):
    if _TEMPLATE_GRAY is None:
        raise RuntimeError("Ink calibration is not initialized.")

    template = resize_nearest(
        _TEMPLATE_GRAY,
        gray.shape,
    )

    template = align_template_gray(
        template,
        gray,
    )

    darkness_gain = (
        template.astype(np.int16)
        - gray.astype(np.int16)
    )

    return (
        (darkness_gain >= TEMPLATE_DIFF_THRESHOLD)
        & (gray < MAX_INK_GRAY)
    )


def page_ink_mask(page):
    return handwriting_mask_from_gray(
        render_page_gray(page)
    )


# =========================================================
# Ink calibration
#
# ink_100.pdf = exactly 100% ink.
# =========================================================

def initialize_ink_calibration():
    global _TEMPLATE_GRAY
    global _REFERENCE_INK_PIXELS

    if not INK_REFERENCE_PDF.exists():
        raise FileNotFoundError(
            f"Missing reference file:\n{INK_REFERENCE_PDF}"
        )

    if not GRID_TEMPLATE_PDF.exists():
        raise FileNotFoundError(
            f"Missing template file:\n{GRID_TEMPLATE_PDF}"
        )

    _TEMPLATE_GRAY = load_first_page_gray(
        GRID_TEMPLATE_PDF
    )

    reference_gray = load_first_page_gray(
        INK_REFERENCE_PDF
    )

    reference_mask = handwriting_mask_from_gray(
        reference_gray
    )

    _REFERENCE_INK_PIXELS = int(
        np.count_nonzero(reference_mask)
    )

    if _REFERENCE_INK_PIXELS <= 0:
        raise RuntimeError(
            "Reference ink amount is zero."
        )

    blank_mask = handwriting_mask_from_gray(
        _TEMPLATE_GRAY
    )

    blank_pixels = int(
        np.count_nonzero(blank_mask)
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
#
# Metadata changes do not count; rendered PDF appearance does.
#
# Important: this exact hash is only a *candidate detector*.  Re-exporting a
# visually identical PDF can still alter anti-aliasing enough to change this
# hash.  Final Modified status is decided later by robust ink-mask comparison.
# =========================================================

def visual_pdf_hash(path):
    h = hashlib.sha256()
    doc = fitz.open(path)

    try:
        h.update(
            str(doc.page_count).encode("utf-8")
        )

        for page_number in range(doc.page_count):
            page = doc.load_page(page_number)

            pix = page.get_pixmap(
                matrix=fitz.Matrix(
                    RENDER_SCALE,
                    RENDER_SCALE,
                ),
                alpha=False,
            )

            h.update(
                str(pix.width).encode("utf-8")
            )
            h.update(
                str(pix.height).encode("utf-8")
            )
            h.update(pix.samples)

        return h.hexdigest()

    finally:
        doc.close()


# =========================================================
# Mask utilities
# =========================================================

def shift_mask(mask, dx, dy):
    height, width = mask.shape

    shifted = np.zeros_like(
        mask,
        dtype=bool,
    )

    src_x1 = max(0, -dx)
    src_x2 = min(width, width - dx)
    src_y1 = max(0, -dy)
    src_y2 = min(height, height - dy)

    dst_x1 = max(0, dx)
    dst_x2 = min(width, width + dx)
    dst_y1 = max(0, dy)
    dst_y2 = min(height, height + dy)

    if (
        src_x1 >= src_x2
        or src_y1 >= src_y2
    ):
        return shifted

    shifted[
        dst_y1:dst_y2,
        dst_x1:dst_x2,
    ] = mask[
        src_y1:src_y2,
        src_x1:src_x2,
    ]

    return shifted


def scale_mask_centered(mask, scale, target_shape=None):
    """Uniformly scale a binary mask around the page center."""
    if target_shape is None:
        target_shape = mask.shape

    target_h, target_w = target_shape
    source_h, source_w = mask.shape

    scaled_h = max(1, int(round(source_h * scale)))
    scaled_w = max(1, int(round(source_w * scale)))

    scaled = resize_nearest(
        mask,
        (scaled_h, scaled_w),
    ).astype(bool)

    result = np.zeros(
        (target_h, target_w),
        dtype=bool,
    )

    src_y1 = max(0, (scaled_h - target_h) // 2)
    src_x1 = max(0, (scaled_w - target_w) // 2)
    dst_y1 = max(0, (target_h - scaled_h) // 2)
    dst_x1 = max(0, (target_w - scaled_w) // 2)

    copy_h = min(
        scaled_h - src_y1,
        target_h - dst_y1,
    )
    copy_w = min(
        scaled_w - src_x1,
        target_w - dst_x1,
    )

    if copy_h > 0 and copy_w > 0:
        result[
            dst_y1:dst_y1 + copy_h,
            dst_x1:dst_x1 + copy_w,
        ] = scaled[
            src_y1:src_y1 + copy_h,
            src_x1:src_x1 + copy_w,
        ]

    return result


def downsample_mask_any(mask, factor):
    """Block-reduce a binary mask while preserving thin handwriting strokes."""
    if factor <= 1:
        return mask.astype(bool)

    height, width = mask.shape
    padded_h = ((height + factor - 1) // factor) * factor
    padded_w = ((width + factor - 1) // factor) * factor

    padded = np.zeros(
        (padded_h, padded_w),
        dtype=bool,
    )
    padded[:height, :width] = mask

    return padded.reshape(
        padded_h // factor,
        factor,
        padded_w // factor,
        factor,
    ).any(axis=(1, 3))


def shifted_overlap_score(old_mask, new_mask, dx, dy):
    """Dice-style overlap score for a translation, without allocating a shift."""
    height, width = new_mask.shape

    src_x1 = max(0, -dx)
    src_x2 = min(width, width - dx)
    src_y1 = max(0, -dy)
    src_y2 = min(height, height - dy)

    dst_x1 = max(0, dx)
    dst_x2 = min(width, width + dx)
    dst_y1 = max(0, dy)
    dst_y2 = min(height, height + dy)

    if src_x1 >= src_x2 or src_y1 >= src_y2:
        return 0.0

    old_view = old_mask[
        src_y1:src_y2,
        src_x1:src_x2,
    ]
    new_view = new_mask[
        dst_y1:dst_y2,
        dst_x1:dst_x2,
    ]

    old_count = int(np.count_nonzero(old_view))
    new_count = int(np.count_nonzero(new_view))

    if old_count == 0 and new_count == 0:
        return 1.0
    if old_count == 0 or new_count == 0:
        return 0.0

    overlap = int(
        np.count_nonzero(old_view & new_view)
    )

    return (
        2.0 * overlap
        / (old_count + new_count)
    )


def align_old_mask(old_mask, new_mask):
    """
    Register old handwriting to new handwriting.

    The earlier implementation searched only +/-8 full-resolution pixels.
    Some PDF re-exports move the entire ink layer farther than that, or change
    its scale by about one or two percent.  Such a change makes almost every
    old stroke look simultaneously removed and re-added.

    This version first searches cheaply on a block-reduced mask over a much
    wider translation window and several tiny uniform scales, then performs a
    small full-resolution refinement around the best result.
    """
    old_mask = resize_nearest(
        old_mask,
        new_mask.shape,
    ).astype(bool)
    new_mask = new_mask.astype(bool)

    if (
        np.count_nonzero(old_mask) == 0
        or np.count_nonzero(new_mask) == 0
    ):
        return old_mask

    factor = GLOBAL_ALIGNMENT_COARSE_FACTOR
    coarse_new = downsample_mask_any(
        new_mask,
        factor,
    )

    coarse_limit = max(
        1,
        int(math.ceil(
            GLOBAL_ALIGNMENT_MAX_SHIFT / factor
        )),
    )

    best_score = -1.0
    best_scale = 1.0
    best_coarse_dx = 0
    best_coarse_dy = 0

    for scale in GLOBAL_ALIGNMENT_SCALES:
        scaled_old = scale_mask_centered(
            old_mask,
            scale,
            new_mask.shape,
        )
        coarse_old = downsample_mask_any(
            scaled_old,
            factor,
        )

        for coarse_dy in range(
            -coarse_limit,
            coarse_limit + 1,
        ):
            for coarse_dx in range(
                -coarse_limit,
                coarse_limit + 1,
            ):
                score = shifted_overlap_score(
                    coarse_old,
                    coarse_new,
                    coarse_dx,
                    coarse_dy,
                )

                if score > best_score:
                    best_score = score
                    best_scale = scale
                    best_coarse_dx = coarse_dx
                    best_coarse_dy = coarse_dy

    scaled_old = scale_mask_centered(
        old_mask,
        best_scale,
        new_mask.shape,
    )

    base_dx = best_coarse_dx * factor
    base_dy = best_coarse_dy * factor

    best_dx = base_dx
    best_dy = base_dy
    best_score = shifted_overlap_score(
        scaled_old,
        new_mask,
        best_dx,
        best_dy,
    )

    refine = GLOBAL_ALIGNMENT_REFINE_RADIUS

    for dy in range(
        base_dy - refine,
        base_dy + refine + 1,
    ):
        if abs(dy) > GLOBAL_ALIGNMENT_MAX_SHIFT:
            continue

        for dx in range(
            base_dx - refine,
            base_dx + refine + 1,
        ):
            if abs(dx) > GLOBAL_ALIGNMENT_MAX_SHIFT:
                continue

            score = shifted_overlap_score(
                scaled_old,
                new_mask,
                dx,
                dy,
            )

            if score > best_score:
                best_score = score
                best_dx = dx
                best_dy = dy

    return shift_mask(
        scaled_old,
        best_dx,
        best_dy,
    )


def dilate_mask(mask, radius):
    if radius <= 0:
        return mask

    result = mask.copy()

    for dy in range(
        -radius,
        radius + 1,
    ):
        for dx in range(
            -radius,
            radius + 1,
        ):
            if dx == 0 and dy == 0:
                continue

            result |= shift_mask(
                mask,
                dx,
                dy,
            )

    return result


def masks_are_render_equivalent(old_mask, new_mask):
    """
    Return True when two page ink masks have the same handwriting structure
    and differ only by small rasterization/export noise.

    The old mask is expected to be already aligned to the new mask.  A wider
    dilation is used *only* for deciding whether the page is structurally the
    same; it is not used for the actual added-ink count.

    We require high coverage in both directions so a genuine new line or note
    does not disappear merely because most of the page stayed unchanged.
    """
    old_count = int(np.count_nonzero(old_mask))
    new_count = int(np.count_nonzero(new_mask))

    if old_count == 0 and new_count == 0:
        return True

    if old_count == 0 or new_count == 0:
        return False

    wide_old = dilate_mask(
        old_mask,
        REEXPORT_TOLERANCE_RADIUS,
    )
    wide_new = dilate_mask(
        new_mask,
        REEXPORT_TOLERANCE_RADIUS,
    )

    new_covered = int(
        np.count_nonzero(
            new_mask & wide_old
        )
    ) / new_count

    old_covered = int(
        np.count_nonzero(
            old_mask & wide_new
        )
    ) / old_count

    mutual_coverage = min(
        new_covered,
        old_covered,
    )

    ink_delta_ratio = (
        abs(new_count - old_count)
        / max(new_count, old_count)
    )

    # Very high structural agreement permits a little more change in raster
    # thickness.  Otherwise require both high agreement and near-equal ink
    # area.  This catches PDFium-style re-exports without hiding real notes.
    if (
        mutual_coverage >= REEXPORT_STRONG_COVERAGE
        and ink_delta_ratio <= REEXPORT_STRONG_MAX_INK_DELTA
    ):
        return True

    if (
        mutual_coverage >= REEXPORT_NORMAL_COVERAGE
        and ink_delta_ratio <= REEXPORT_NORMAL_MAX_INK_DELTA
    ):
        return True

    # Pathological re-export fallback.
    #
    # If a raster/export transform moves many old pixels and creates nearly the
    # same amount of apparently new pixels, the change is symmetric.  Real
    # note-taking is usually directional: added ink has no matching amount of
    # vanished ink.  Requiring both balanced churn and high coarse structural
    # similarity keeps small genuine additions visible while suppressing the
    # "whole page rewritten" false positive.
    narrow_old = dilate_mask(
        old_mask,
        OLD_INK_TOLERANCE_RADIUS,
    )
    narrow_new = dilate_mask(
        new_mask,
        OLD_INK_TOLERANCE_RADIUS,
    )

    apparent_added = int(
        np.count_nonzero(
            new_mask & ~narrow_old
        )
    )
    apparent_removed = int(
        np.count_nonzero(
            old_mask & ~narrow_new
        )
    )

    churn_max = max(
        apparent_added,
        apparent_removed,
    )

    if churn_max <= 0:
        return True

    churn_ratio = (
        apparent_added + apparent_removed
    ) / max(old_count, new_count)

    churn_symmetry = (
        min(apparent_added, apparent_removed)
        / churn_max
    )

    coarse_similarity = page_signature_similarity(
        page_signature(old_mask),
        page_signature(new_mask),
    )

    return (
        coarse_similarity
        >= REEXPORT_BALANCED_COARSE_SIMILARITY
        and churn_ratio
        >= REEXPORT_BALANCED_MIN_CHURN
        and churn_symmetry
        >= REEXPORT_BALANCED_MIN_SYMMETRY
        and ink_delta_ratio
        <= REEXPORT_BALANCED_MAX_INK_DELTA
    )


# =========================================================
# Page-sequence alignment
#
# A single inserted/deleted page must not make every later page look changed.
# Pages are first represented by coarse handwriting-density signatures, then a
# monotone dynamic-programming alignment determines their correspondence.
# =========================================================

def page_signature(mask):
    """Return a coarse handwriting-density signature for one page mask."""
    row_blocks = np.array_split(
        mask.astype(np.float32),
        PAGE_SIGNATURE_ROWS,
        axis=0,
    )

    signature = np.zeros(
        (PAGE_SIGNATURE_ROWS, PAGE_SIGNATURE_COLS),
        dtype=np.float32,
    )

    for row_index, row_block in enumerate(row_blocks):
        col_blocks = np.array_split(
            row_block,
            PAGE_SIGNATURE_COLS,
            axis=1,
        )

        for col_index, cell in enumerate(col_blocks):
            if cell.size:
                signature[row_index, col_index] = float(cell.mean())

    return signature


def page_signature_similarity(old_signature, new_signature):
    """
    Compare two coarse page signatures in [0, 1].

    The score combines cosine similarity (where the writing is), coarse
    occupancy overlap, and total-ink ratio.  This is deliberately tolerant of
    small additions and PDF re-export jitter while still distinguishing nearby
    pages in a sequence.
    """
    old_vector = old_signature.ravel()
    new_vector = new_signature.ravel()

    old_mass = float(old_vector.sum())
    new_mass = float(new_vector.sum())

    if old_mass <= 1e-9 and new_mass <= 1e-9:
        return 1.0

    if old_mass <= 1e-9 or new_mass <= 1e-9:
        return 0.0

    old_norm = float(np.linalg.norm(old_vector))
    new_norm = float(np.linalg.norm(new_vector))

    cosine = float(
        np.dot(old_vector, new_vector)
        / max(old_norm * new_norm, 1e-9)
    )
    cosine = max(0.0, min(1.0, cosine))

    # A cell is considered occupied if at least a tiny amount of ink lands in
    # it.  Coarse occupancy is much less sensitive to a few-pixel shift than
    # an exact rendered-page comparison.
    old_occupied = old_signature > 0.002
    new_occupied = new_signature > 0.002

    intersection = int(
        np.count_nonzero(old_occupied & new_occupied)
    )
    occupied_total = int(
        np.count_nonzero(old_occupied)
        + np.count_nonzero(new_occupied)
    )

    dice = (
        2.0 * intersection / occupied_total
        if occupied_total > 0
        else 1.0
    )

    mass_ratio = (
        min(old_mass, new_mass)
        / max(old_mass, new_mass)
    )

    similarity = (
        0.60 * cosine
        + 0.25 * dice
        + 0.15 * mass_ratio
    )

    return max(0.0, min(1.0, float(similarity)))


def load_pdf_ink_masks(pdf_path):
    """Render every page of a PDF once and return its handwriting masks."""
    doc = fitz.open(pdf_path)

    try:
        return [
            page_ink_mask(
                doc.load_page(page_number)
            )
            for page_number in range(doc.page_count)
        ]

    finally:
        doc.close()


def align_page_sequences(old_masks, new_masks):
    """
    Return monotone old/new page correspondence.

    The result has:
      - ``pairs``: (old_index, new_index, similarity)
      - ``unmatched_old``: deleted pages
      - ``unmatched_new``: inserted/appended pages

    This is a Needleman-Wunsch-style alignment over page signatures.  It
    preserves order, which is exactly what we want for ordinary note editing:
    inserting a page shifts later indices but does not reorder the document.
    """
    old_signatures = [
        page_signature(mask)
        for mask in old_masks
    ]
    new_signatures = [
        page_signature(mask)
        for mask in new_masks
    ]

    old_count = len(old_masks)
    new_count = len(new_masks)

    scores = np.full(
        (old_count + 1, new_count + 1),
        -np.inf,
        dtype=np.float64,
    )
    back = [
        [None] * (new_count + 1)
        for _ in range(old_count + 1)
    ]

    scores[0, 0] = 0.0

    for old_index in range(1, old_count + 1):
        scores[old_index, 0] = (
            scores[old_index - 1, 0]
            + PAGE_GAP_PENALTY
        )
        back[old_index][0] = "old_gap"

    for new_index in range(1, new_count + 1):
        scores[0, new_index] = (
            scores[0, new_index - 1]
            + PAGE_GAP_PENALTY
        )
        back[0][new_index] = "new_gap"

    similarity_cache = {}

    def similarity(old_index, new_index):
        key = (old_index, new_index)
        if key not in similarity_cache:
            similarity_cache[key] = page_signature_similarity(
                old_signatures[old_index],
                new_signatures[new_index],
            )
        return similarity_cache[key]

    for old_index in range(1, old_count + 1):
        for new_index in range(1, new_count + 1):
            page_similarity = similarity(
                old_index - 1,
                new_index - 1,
            )

            # Matching is rewarded only above a neutral baseline.  Two gaps
            # beat an obviously unrelated page pair, while a moderately edited
            # same page still remains matchable.
            match_score = (
                page_similarity
                - PAGE_MATCH_BASELINE
            )

            diagonal = (
                scores[old_index - 1, new_index - 1]
                + match_score
            )
            old_gap = (
                scores[old_index - 1, new_index]
                + PAGE_GAP_PENALTY
            )
            new_gap = (
                scores[old_index, new_index - 1]
                + PAGE_GAP_PENALTY
            )

            best_score = diagonal
            best_move = "match"

            if old_gap > best_score:
                best_score = old_gap
                best_move = "old_gap"

            if new_gap > best_score:
                best_score = new_gap
                best_move = "new_gap"

            scores[old_index, new_index] = best_score
            back[old_index][new_index] = best_move

    pairs = []
    unmatched_old = []
    unmatched_new = []

    old_index = old_count
    new_index = new_count

    while old_index > 0 or new_index > 0:
        move = back[old_index][new_index]

        if move == "match":
            similarity_value = similarity(
                old_index - 1,
                new_index - 1,
            )

            # Extremely weak diagonal matches are safer to interpret as one
            # deletion plus one insertion.  This prevents unrelated pages from
            # being forced together merely because both sequences are short.
            if similarity_value < PAGE_MIN_REPORTED_MATCH:
                unmatched_old.append(old_index - 1)
                unmatched_new.append(new_index - 1)
            else:
                pairs.append((
                    old_index - 1,
                    new_index - 1,
                    similarity_value,
                ))

            old_index -= 1
            new_index -= 1

        elif move == "old_gap":
            unmatched_old.append(old_index - 1)
            old_index -= 1

        elif move == "new_gap":
            unmatched_new.append(new_index - 1)
            new_index -= 1

        else:
            # Defensive fallback; normally unreachable except at (0, 0).
            if old_index > 0:
                unmatched_old.append(old_index - 1)
                old_index -= 1
            elif new_index > 0:
                unmatched_new.append(new_index - 1)
                new_index -= 1

    pairs.reverse()
    unmatched_old.reverse()
    unmatched_new.reverse()

    return {
        "pairs": pairs,
        "unmatched_old": unmatched_old,
        "unmatched_new": unmatched_new,
    }


# =========================================================
# Ink calculations
# =========================================================

def count_total_ink_pixels(pdf_path):
    total = 0
    doc = fitz.open(pdf_path)

    try:
        for page_number in range(doc.page_count):
            mask = page_ink_mask(
                doc.load_page(page_number)
            )

            total += int(
                np.count_nonzero(mask)
            )

        return total

    finally:
        doc.close()


def compare_pdf_ink(
    old_pdf_path,
    new_pdf_path,
):
    """
    Compare two PDF versions after aligning their page sequences.

    Returns:
        (added_ink_pixels, meaningful_change)

    Important behaviors:
      - inserted/deleted middle pages do not shift every later comparison;
      - re-export-only raster changes remain ignored;
      - unmatched new pages count all handwriting as newly added ink;
      - unmatched old pages mark the PDF as meaningfully changed, but add no ink.
    """
    old_masks = load_pdf_ink_masks(
        old_pdf_path
    )
    new_masks = load_pdf_ink_masks(
        new_pdf_path
    )

    page_alignment = align_page_sequences(
        old_masks,
        new_masks,
    )

    total_added = 0
    meaningful_change = bool(
        page_alignment["unmatched_old"]
        or page_alignment["unmatched_new"]
    )

    # Compare only pages selected as actual counterparts by the sequence
    # alignment.  This is what makes middle-page insertion safe.
    for old_index, new_index, _similarity in page_alignment["pairs"]:
        old_mask = old_masks[old_index]
        new_mask = new_masks[new_index]

        old_mask = align_old_mask(
            old_mask,
            new_mask,
        )

        # Silent PDF re-export / anti-aliasing changes are not real note edits.
        if masks_are_render_equivalent(
            old_mask,
            new_mask,
        ):
            continue

        meaningful_change = True

        old_tolerant = dilate_mask(
            old_mask,
            OLD_INK_TOLERANCE_RADIUS,
        )

        added_mask = (
            new_mask
            & ~old_tolerant
        )

        total_added += int(
            np.count_nonzero(added_mask)
        )

    # A page that exists only in the new PDF is a genuine insertion/appending.
    # Count its entire handwriting content as new ink.
    for new_index in page_alignment["unmatched_new"]:
        total_added += int(
            np.count_nonzero(
                new_masks[new_index]
            )
        )

    return total_added, meaningful_change


def count_added_ink_pixels(
    old_pdf_path,
    new_pdf_path,
):
    """Compatibility wrapper returning only the added-ink pixel count."""
    pixels, _ = compare_pdf_ink(
        old_pdf_path,
        new_pdf_path,
    )
    return pixels


def ink_percent(pixel_count):
    if _REFERENCE_INK_PIXELS is None:
        raise RuntimeError(
            "Ink calibration is not initialized."
        )

    return (
        pixel_count
        / _REFERENCE_INK_PIXELS
        * 100.0
    )


def rounded_ink_percent(pixel_count):
    return round(
        ink_percent(pixel_count),
        1,
    )


# =========================================================
# Snapshot
# =========================================================

def get_pdf_snapshot(date_dir):
    snapshot = {}

    all_pdf_paths = sorted(
        path
        for path in date_dir.rglob("*")
        if (
            path.is_file()
            and path.suffix.lower() == ".pdf"
        )
    )

    pdf_paths = [
        path
        for path in all_pdf_paths
        if is_note_pdf(date_dir, path)
    ]

    for path in pdf_paths:
        relative_path = (
            path.relative_to(date_dir)
            .as_posix()
        )

        print(
            f"Hashing "
            f"[{date_dir.name}] "
            f"{relative_path}"
        )

        snapshot[relative_path] = {
            "hash": visual_pdf_hash(path),
            "name": path.name,
        }

    return snapshot


# =========================================================
# Moved / Renamed detection
# =========================================================

def detect_moves(
    previous,
    current,
    deleted_candidates,
    added_candidates,
):
    moved = []

    # -----------------------------------------------------
    # STEP 1:
    # Same subject + same normalized filename.
    # This can still match a moved file whose contents changed.
    # -----------------------------------------------------

    old_by_identity = defaultdict(list)
    new_by_identity = defaultdict(list)

    for path in deleted_candidates:
        key = (
            top_subject(path),
            normalized_filename(path),
        )
        old_by_identity[key].append(path)

    for path in added_candidates:
        key = (
            top_subject(path),
            normalized_filename(path),
        )
        new_by_identity[key].append(path)

    common_keys = (
        set(old_by_identity)
        & set(new_by_identity)
    )

    for key in sorted(common_keys):
        old_list = sorted(
            old_by_identity[key]
        )
        new_list = sorted(
            new_by_identity[key]
        )

        if (
            len(old_list) == 1
            and len(new_list) == 1
        ):
            old_path = old_list[0]
            new_path = new_list[0]

            moved.append({
                "from": old_path,
                "to": new_path,
            })

            deleted_candidates.remove(
                old_path
            )
            added_candidates.remove(
                new_path
            )

    # -----------------------------------------------------
    # STEP 2:
    # Same visual hash + same subject + sufficiently similar name.
    # Ambiguous hash groups are deliberately left as Added/Removed.
    # -----------------------------------------------------

    deleted_by_hash = defaultdict(list)
    added_by_hash = defaultdict(list)

    for path in deleted_candidates:
        deleted_by_hash[
            previous[path]["hash"]
        ].append(path)

    for path in added_candidates:
        added_by_hash[
            current[path]["hash"]
        ].append(path)

    common_hashes = (
        set(deleted_by_hash)
        & set(added_by_hash)
    )

    for file_hash in sorted(common_hashes):
        old_paths = [
            path
            for path in deleted_by_hash[file_hash]
            if path in deleted_candidates
        ]

        new_paths = [
            path
            for path in added_by_hash[file_hash]
            if path in added_candidates
        ]

        if (
            len(old_paths) != 1
            or len(new_paths) != 1
        ):
            continue

        old_path = old_paths[0]
        new_path = new_paths[0]

        if (
            top_subject(old_path)
            != top_subject(new_path)
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
            new_name,
        ).ratio()

        if (
            old_name != new_name
            and similarity
            < RENAME_SIMILARITY_THRESHOLD
        ):
            continue

        moved.append({
            "from": old_path,
            "to": new_path,
        })

        deleted_candidates.remove(
            old_path
        )
        added_candidates.remove(
            new_path
        )

    return moved


# =========================================================
# File tree stored in YAML
#
# This is what lets old versions keep their file/folder lists
# even though the old PDFs are not uploaded to GitHub.
# =========================================================

def build_subject_tree(
    snapshot,
    file_ink_percent,
    subject_ink_percent,
    folder_ink_percent,
    include_urls=False,
):
    """
    Build a true recursive tree:

        Subject
        ├─ files directly under the subject
        └─ folders
           ├─ files
           └─ folders
              └─ ...

    Folder depth is unlimited. For nested PDFs, the first path component is
    the subject and every later directory component becomes one recursive
    node. Top-level PDFs are collected under ``Others``.
    """
    subject_nodes = {}

    def make_folder_node(name, raw_path):
        return {
            "name": name,
            "label": name,
            "raw_path": raw_path,
            "files": [],
            "folders": {},
        }

    for path in sorted(snapshot):
        parts = list(PurePosixPath(path).parts)

        # A PDF directly under the dated snapshot has no natural subject.
        # Keep it, but place it in a synthetic ``Others`` section.
        if len(parts) == 1:
            subject = "Others"
            folder_parts = []
        else:
            subject = parts[0]
            folder_parts = parts[1:-1]

        subject_node = subject_nodes.setdefault(
            subject,
            {
                "name": subject,
                "files": [],
                "folders": {},
            },
        )

        file_item = {
            "name": strip_pdf_suffixes(Path(path).name),
            "raw_path": path,
            "ink_added_percent": file_ink_percent.get(path, 0.0),
        }

        if include_urls:
            file_item["url"] = published_url(path)

        # A PDF directly under the subject has no extra folder node.
        if not folder_parts:
            subject_node["files"].append(file_item)
            continue

        current_folders = subject_node["folders"]
        raw_parts = [subject]
        current_node = None

        for folder_name in folder_parts:
            raw_parts.append(folder_name)
            raw_path = "/".join(raw_parts)

            current_node = current_folders.setdefault(
                folder_name,
                make_folder_node(folder_name, raw_path),
            )
            current_folders = current_node["folders"]

        current_node["files"].append(file_item)

    def finalize_folder(node):
        children = [
            finalize_folder(node["folders"][name])
            for name in sorted(node["folders"])
        ]

        return {
            "name": node["name"],
            "label": node["label"],
            "raw_path": node["raw_path"],
            "ink_added_percent": folder_ink_percent.get(
                node["raw_path"],
                0.0,
            ),
            "files": sorted(
                node["files"],
                key=lambda item: item["name"].lower(),
            ),
            "folders": children,
        }

    subjects = []

    for subject in sorted(subject_nodes, key=subject_sort_key):
        node = subject_nodes[subject]

        subjects.append({
            "name": subject,
            "ink_added_percent": subject_ink_percent.get(subject, 0.0),
            "files": sorted(
                node["files"],
                key=lambda item: item["name"].lower(),
            ),
            "folders": [
                finalize_folder(node["folders"][name])
                for name in sorted(node["folders"])
            ],
        })

    return subjects


def snapshot_from_stored_subjects(subjects):
    """Recover the historical PDF path list from either schema v1 or v2."""
    snapshot = {}

    def add_file(file_item, fallback_parent=None):
        raw_path = file_item.get("raw_path")

        if not raw_path and fallback_parent:
            # Compatibility fallback for very old data.
            raw_path = (
                fallback_parent.rstrip("/")
                + "/"
                + str(file_item.get("name", "")).rstrip()
                + ".pdf"
            )

        if raw_path:
            snapshot[str(raw_path)] = {
                "name": Path(str(raw_path)).name,
            }

    def walk_folder(folder):
        raw_path = folder.get("raw_path")

        for file_item in folder.get("files", []) or []:
            add_file(file_item, raw_path)

        for child in folder.get("folders", []) or []:
            walk_folder(child)

    for subject in subjects or []:
        subject_name = str(subject.get("name", ""))

        for file_item in subject.get("files", []) or []:
            add_file(file_item, subject_name)

        for folder in subject.get("folders", []) or []:
            walk_folder(folder)

    return snapshot


def cumulative_folder_percent_from_legacy(folder_ink_percent):
    """
    Convert schema-v1 leaf-folder ink totals into recursive subtotals.

    Old records counted ink only in the PDF's immediate parent folder.
    Recursive folders should show the total of every descendant, so each
    old leaf subtotal is propagated to all of its ancestors below subject.
    """
    cumulative = defaultdict(float)

    for raw_folder, value in (folder_ink_percent or {}).items():
        if raw_folder == "General":
            continue

        parts = str(raw_folder).split("/")

        if len(parts) < 2:
            continue

        numeric_value = float(value or 0.0)

        for depth in range(2, len(parts) + 1):
            cumulative["/".join(parts[:depth])] += numeric_value

    return {
        key: round(value, 1)
        for key, value in sorted(cumulative.items())
    }


def migrate_record_tree_to_v2(record):
    """One-time structural migration for frozen schema-v1 history."""
    if not record:
        return record

    snapshot = snapshot_from_stored_subjects(
        record.get("subjects", [])
    )

    recursive_folder_ink = cumulative_folder_percent_from_legacy(
        record.get("folder_ink_percent", {})
    )

    record["folder_ink_percent"] = recursive_folder_ink
    record["subjects"] = build_subject_tree(
        snapshot,
        record.get("file_ink_percent", {}) or {},
        record.get("subject_ink_percent", {}) or {},
        recursive_folder_ink,
        include_urls=False,
    )

    return record


def migrate_record_tree_to_v3(record):
    """Rename the old top-level ``General`` bucket to ``Others``."""
    if not record:
        return record

    snapshot = snapshot_from_stored_subjects(
        record.get("subjects", [])
    )

    subject_ink = dict(
        record.get("subject_ink_percent", {}) or {}
    )

    if "General" in subject_ink:
        subject_ink["Others"] = round(
            float(subject_ink.get("Others", 0.0))
            + float(subject_ink.pop("General", 0.0)),
            1,
        )

    folder_ink = dict(
        record.get("folder_ink_percent", {}) or {}
    )

    # In older schemas the root bucket could be called General.
    # It is not a real folder in the recursive tree, so drop that subtotal.
    folder_ink.pop("General", None)

    record["subject_ink_percent"] = subject_ink
    record["folder_ink_percent"] = folder_ink
    record["subjects"] = build_subject_tree(
        snapshot,
        record.get("file_ink_percent", {}) or {},
        subject_ink,
        folder_ink,
        include_urls=False,
    )

    return record


# =========================================================
# Publish only the newest snapshot, including top-level PDFs
#
# Local dated folders stay under untexed/ and are never copied
# to GitHub.  untexed-current/ is replaced on every run.
# =========================================================

def publish_latest_snapshot(
    latest_date_dir
):
    if PUBLISHED_ROOT.exists():
        shutil.rmtree(
            PUBLISHED_ROOT
        )

    PUBLISHED_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    for source in sorted(
        latest_date_dir.rglob("*")
    ):
        if not is_note_pdf(
            latest_date_dir,
            source,
        ):
            continue

        relative = source.relative_to(
            latest_date_dir
        )

        destination = (
            PUBLISHED_ROOT
            / relative
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            source,
            destination,
        )

    print()
    print(
        f"Published latest snapshot "
        f"{latest_date_dir.name} -> "
        f"{PUBLISHED_ROOT}"
    )


# =========================================================
# Rolling-history helpers
# =========================================================

def parse_snapshot_date(name):
    """Parse a YYMMDD snapshot key into a calendar date."""
    try:
        return datetime.strptime(str(name), "%y%m%d").date()
    except ValueError as exc:
        raise ValueError(
            f"Invalid snapshot date '{name}'. Expected YYMMDD."
        ) from exc


def load_existing_history():
    """Load committed YAML and preserve frozen records across runs."""
    if not OUTPUT.exists():
        return {
            "latest_date": None,
            "dates": [],
            "records": {},
            "tree_schema_version": TREE_SCHEMA_VERSION,
        }

    with OUTPUT.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file) or {}

    raw_records = loaded.get("records", {}) or {}
    records = {
        str(date): record
        for date, record in raw_records.items()
    }
    dates = [
        str(date)
        for date in (loaded.get("dates", []) or [])
    ]

    stored_schema = int(
        loaded.get("tree_schema_version", 1) or 1
    )

    if stored_schema < 2:
        print()
        print(
            "Migrating stored folder history to recursive tree schema..."
        )

        records = {
            date: migrate_record_tree_to_v2(record)
            for date, record in records.items()
        }

    if stored_schema < 3:
        print()
        print(
            "Migrating top-level General history to Others..."
        )

        records = {
            date: migrate_record_tree_to_v3(record)
            for date, record in records.items()
        }

    return {
        "latest_date": (
            str(loaded["latest_date"])
            if loaded.get("latest_date") is not None
            else None
        ),
        "dates": dates,
        "records": records,
        "tree_schema_version": TREE_SCHEMA_VERSION,
    }


def build_baseline_record(current):
    return {
        "baseline": True,
        "total_ink_percent": None,
        "library_total_ink_percent": None,
        "subject_ink_percent": {},
        "folder_ink_percent": {},
        "file_ink_percent": {},
        "subjects": build_subject_tree(
            current, {}, {}, {}, include_urls=False
        ),
        "added": [],
        "modified": [],
        "moved_renamed": [],
        "deleted": [],
    }


def build_comparison_record(previous_dir, date_dir, previous, current):
    """Build one day's Record by comparing two consecutive snapshots."""
    previous_paths = set(previous)
    current_paths = set(current)
    common_paths = previous_paths & current_paths

    modified_raw = sorted(
        path
        for path in common_paths
        if previous[path]["hash"] != current[path]["hash"]
    )
    added_candidates = set(current_paths - previous_paths)
    deleted_candidates = set(previous_paths - current_paths)

    moved_raw = detect_moves(
        previous,
        current,
        deleted_candidates,
        added_candidates,
    )

    total_added_ink_pixels = 0
    file_ink_pixels = defaultdict(int)
    folder_ink_pixels = defaultdict(int)
    subject_ink_pixels = defaultdict(int)

    def register_ink(relative_path, pixels):
        nonlocal total_added_ink_pixels
        total_added_ink_pixels += pixels
        file_ink_pixels[relative_path] += pixels

        # Every recursive folder shows the subtotal of all descendants.
        for folder in folder_ancestor_keys(relative_path):
            folder_ink_pixels[folder] += pixels

        subject_ink_pixels[subject_key(relative_path)] += pixels

    added = []
    for path in sorted(added_candidates):
        current_pdf = date_dir / Path(path)
        pixels = count_total_ink_pixels(current_pdf)
        register_ink(path, pixels)
        added.append({
            "path": display_path(path),
            "ink_added_percent": rounded_ink_percent(pixels),
        })

    modified = []
    for path in modified_raw:
        old_pdf = previous_dir / Path(path)
        new_pdf = date_dir / Path(path)

        pixels, meaningful_change = compare_pdf_ink(
            old_pdf,
            new_pdf,
        )

        if not meaningful_change:
            print(
                f"Ignoring render-only PDF change: {path}"
            )
            continue

        register_ink(path, pixels)
        modified.append({
            "path": display_path(path),
            "ink_added_percent": rounded_ink_percent(pixels),
        })

    deleted = [
        display_path(path)
        for path in sorted(deleted_candidates)
    ]

    moved_renamed = []
    for item in sorted(
        moved_raw,
        key=lambda value: (value["from"], value["to"]),
    ):
        old_path = item["from"]
        new_path = item["to"]
        move_item = {
            "from": display_path(old_path),
            "to": display_path(new_path),
            "ink_added_percent": 0.0,
        }

        if previous[old_path]["hash"] != current[new_path]["hash"]:
            old_pdf = previous_dir / Path(old_path)
            new_pdf = date_dir / Path(new_path)

            pixels, meaningful_change = compare_pdf_ink(
                old_pdf,
                new_pdf,
            )

            if meaningful_change:
                register_ink(new_path, pixels)
                move_item["ink_added_percent"] = rounded_ink_percent(pixels)

        moved_renamed.append(move_item)

    file_ink_percent = {
        path: rounded_ink_percent(pixels)
        for path, pixels in sorted(file_ink_pixels.items())
    }
    folder_ink_percent = {
        folder: rounded_ink_percent(pixels)
        for folder, pixels in sorted(folder_ink_pixels.items())
    }
    subject_ink_percent = {
        subject: rounded_ink_percent(pixels)
        for subject, pixels in sorted(subject_ink_pixels.items())
    }

    return {
        "baseline": False,
        "total_ink_percent": rounded_ink_percent(total_added_ink_pixels),
        "library_total_ink_percent": None,
        "subject_ink_percent": subject_ink_percent,
        "folder_ink_percent": folder_ink_percent,
        "file_ink_percent": file_ink_percent,
        "subjects": build_subject_tree(
            current,
            file_ink_percent,
            subject_ink_percent,
            folder_ink_percent,
            include_urls=False,
        ),
        "added": added,
        "modified": modified,
        "moved_renamed": moved_renamed,
        "deleted": deleted,
    }


# =========================================================
# Main
# =========================================================

def main():
    initialize_ink_calibration()

    if not SNAPSHOT_ROOT.exists():
        print(
            f"Snapshot directory not found: {SNAPSHOT_ROOT}"
        )
        return

    date_dirs = sorted(
        [
            path
            for path
            in SNAPSHOT_ROOT.iterdir()
            if (
                path.is_dir()
                and path.name.isdigit()
                and len(path.name) == 6
            )
        ],
        key=lambda path: parse_snapshot_date(
            path.name
        ),
    )

    if not date_dirs:
        print(
            "No dated folders found."
        )
        return

    existing_data = load_existing_history()
    existing_records = existing_data[
        "records"
    ]

    latest_date_dir = date_dirs[-1]
    latest_date = latest_date_dir.name

    local_dir_by_date = {
        path.name: path
        for path in date_dirs
    }

    # =====================================================
    # Snapshot-count rolling history
    # =====================================================
    #
    # The newest ROLLING_SNAPSHOTS snapshot dates stay mutable.
    # One immediately preceding snapshot is scanned only as an
    # anchor so the oldest mutable Record can be compared against
    # the correct predecessor.
    #
    # Important:
    # Use the union of stored Record dates and local snapshot dates.
    # This prevents a missing recent local folder from being silently
    # skipped and causing a later Record to be compared with the
    # wrong predecessor.
    # =====================================================

    all_known_dates = sorted(
        (
            set(existing_records)
            |
            set(local_dir_by_date)
        ),
        key=parse_snapshot_date,
    )

    active_date_keys = (
        all_known_dates[
            -ROLLING_SNAPSHOTS:
        ]
    )
    active_date_set = set(
        active_date_keys
    )

    anchor_date = (
        all_known_dates[
            -ROLLING_SNAPSHOTS - 1
        ]
        if (
            len(all_known_dates)
            > ROLLING_SNAPSHOTS
        )
        else None
    )

    print("Found local versions:")
    print()

    for date_dir in date_dirs:
        print(
            f"  {date_dir.name}"
        )

    print()
    print(
        f"Rolling window : newest "
        f"{ROLLING_SNAPSHOTS} snapshots"
    )

    # =====================================================
    # First run / bootstrap
    # =====================================================
    # If no YAML exists yet, calculate every local snapshot once.
    # On subsequent runs, only the newest N snapshots are mutable.

    bootstrap = not bool(
        existing_records
    )

    if bootstrap:
        print(
            "History mode   : bootstrap (all local snapshots)"
        )

        frozen_records = {}
        scan_dirs = list(
            date_dirs
        )
        active_dirs = list(
            date_dirs
        )
        anchor_dir = None

        print(
            "Recalculate    : all local snapshots"
        )

    else:
        print(
            "History mode   : rolling + frozen history"
        )

        # -----------------------------------------------
        # Safety check:
        # Every date in the newest-N window must exist locally.
        #
        # Example:
        # stored = 260815, 260816
        # local  = 260815, 260817
        #
        # newest 3 known dates = 260815, 260816, 260817.
        # Since 260816 is missing locally, abort instead of
        # comparing 260817 against 260815.
        # -----------------------------------------------

        missing_active_dates = [
            date
            for date in active_date_keys
            if date not in local_dir_by_date
        ]

        if missing_active_dates:
            missing_text = ", ".join(
                missing_active_dates
            )
            raise RuntimeError(
                "A snapshot inside the newest "
                f"{ROLLING_SNAPSHOTS}-snapshot rolling window "
                "is missing locally. Refusing to recalculate, "
                "because that could change later Records.\n"
                f"Missing: {missing_text}\n"
                "Restore those local snapshot folders first."
            )

        active_dirs = [
            local_dir_by_date[date]
            for date in active_date_keys
        ]

        # -----------------------------------------------
        # Freeze every stored Record outside the newest-N
        # snapshot window verbatim.
        # -----------------------------------------------

        frozen_records = {
            date: record
            for date, record
            in existing_records.items()
            if date not in active_date_set
        }

        # -----------------------------------------------
        # The exact immediately preceding known snapshot is
        # the only valid anchor. If frozen history exists and
        # that snapshot folder was deleted locally, abort.
        # -----------------------------------------------

        anchor_dir = (
            local_dir_by_date.get(
                anchor_date
            )
            if anchor_date is not None
            else None
        )

        if (
            anchor_date is not None
            and anchor_dir is None
        ):
            raise RuntimeError(
                "The snapshot immediately preceding the newest "
                f"{ROLLING_SNAPSHOTS}-snapshot window is missing "
                "locally.\n"
                f"Required anchor: {anchor_date}\n"
                "Keep that one predecessor snapshot folder so the "
                "oldest active Record can be compared correctly."
            )

        scan_dirs = []

        if anchor_dir is not None:
            scan_dirs.append(
                anchor_dir
            )

        scan_dirs.extend(
            active_dirs
        )

        print(
            "Recalculate    : "
            + ", ".join(
                active_date_keys
            )
        )
        print(
            f"Frozen records : {len(frozen_records)}"
        )

        if anchor_dir is not None:
            print(
                f"Anchor snapshot: {anchor_dir.name}"
            )
        else:
            print(
                "Anchor snapshot: none"
            )

        # An old local folder outside the mutable window that
        # has no stored Record is not silently inserted into
        # history. It may still be used as the exact anchor.
        ignored_old_local = [
            path.name
            for path in date_dirs
            if (
                path.name not in active_date_set
                and path.name != anchor_date
                and path.name not in existing_records
            )
        ]

        if ignored_old_local:
            print()
            print(
                "Warning: old local snapshots without stored "
                "Records are outside the rolling window and "
                "will be ignored:"
            )
            for date in ignored_old_local:
                print(
                    f"  {date}"
                )

    print()

    # =====================================================
    # Scan only what is needed
    # =====================================================

    snapshots = {}

    for date_dir in scan_dirs:
        print("=" * 70)
        print(
            f"Scanning {date_dir.name}"
        )
        print("=" * 70)
        print()

        snapshots[
            date_dir.name
        ] = get_pdf_snapshot(
            date_dir
        )

        print()

    # =====================================================
    # Build / update records
    # =====================================================

    records = dict(
        frozen_records
    )

    if bootstrap:
        for index, date_dir in enumerate(
            active_dirs
        ):
            date = date_dir.name
            current = snapshots[date]

            if index == 0:
                records[date] = (
                    build_baseline_record(
                        current
                    )
                )
                continue

            previous_dir = active_dirs[
                index - 1
            ]
            previous = snapshots[
                previous_dir.name
            ]

            records[date] = (
                build_comparison_record(
                    previous_dir,
                    date_dir,
                    previous,
                    current,
                )
            )

    else:
        # Recalculate only the newest N snapshot folders.
        # Frozen records remain untouched.
        for index, date_dir in enumerate(
            active_dirs
        ):
            date = date_dir.name
            current = snapshots[date]

            if index == 0:
                if anchor_dir is not None:
                    previous_dir = anchor_dir
                    previous = snapshots[
                        anchor_dir.name
                    ]

                    records[date] = (
                        build_comparison_record(
                            previous_dir,
                            date_dir,
                            previous,
                            current,
                        )
                    )
                elif not frozen_records:
                    records[date] = (
                        build_baseline_record(
                            current
                        )
                    )
                else:
                    raise RuntimeError(
                        "Cannot determine the predecessor of "
                        f"{date}."
                    )

                continue

            previous_dir = active_dirs[
                index - 1
            ]
            previous = snapshots[
                previous_dir.name
            ]

            records[date] = (
                build_comparison_record(
                    previous_dir,
                    date_dir,
                    previous,
                    current,
                )
            )

    # =====================================================
    # Absolute total ink of all PDFs in newest snapshot
    # =====================================================

    if latest_date not in snapshots:
        # This should never happen because latest is always
        # inside the rolling window, but keep the failure clear.
        raise RuntimeError(
            f"Latest snapshot {latest_date} was not scanned."
        )

    library_total_ink_pixels = 0

    print()
    print("=" * 70)
    print(
        "Calculating total library ink"
    )
    print("=" * 70)
    print()

    for relative_path in sorted(
        snapshots[
            latest_date
        ].keys()
    ):
        pdf_path = (
            latest_date_dir
            / Path(relative_path)
        )

        print(
            f"Total ink: "
            f"{relative_path}"
        )

        library_total_ink_pixels += (
            count_total_ink_pixels(
                pdf_path
            )
        )

    records[
        latest_date
    ][
        "library_total_ink_percent"
    ] = rounded_ink_percent(
        library_total_ink_pixels
    )

    # Rebuild newest tree with live URLs.
    records[
        latest_date
    ][
        "subjects"
    ] = build_subject_tree(
        snapshots[latest_date],
        records[
            latest_date
        ][
            "file_ink_percent"
        ],
        records[
            latest_date
        ][
            "subject_ink_percent"
        ],
        records[
            latest_date
        ][
            "folder_ink_percent"
        ],
        include_urls=True,
    )

    # =====================================================
    # Mirror only newest PDFs into tracked publish directory
    # =====================================================

    publish_latest_snapshot(
        latest_date_dir
    )

    # =====================================================
    # YAML
    # =====================================================

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # The date list comes from Records, not from local folders.
    # Therefore deleting frozen local snapshots never removes
    # them from Previous Versions.
    all_record_dates = sorted(
        records,
        key=parse_snapshot_date,
        reverse=True,
    )

    data = {
        "tree_schema_version":
            TREE_SCHEMA_VERSION,
        "latest_date":
            latest_date,
        "dates":
            all_record_dates,
        "history_policy": {
            "rolling_snapshots":
                ROLLING_SNAPSHOTS,
            "active_dates":
                active_date_keys,
            "anchor_date":
                (
                    anchor_dir.name
                    if anchor_dir is not None
                    else None
                ),
        },
        "records":
            records,
    }

    with OUTPUT.open(
        "w",
        encoding="utf-8",
    ) as file:
        yaml.safe_dump(
            data,
            file,
            allow_unicode=True,
            sort_keys=False,
            width=180,
        )

    # =====================================================
    # Summary
    # =====================================================

    print()
    print("=" * 70)
    print("Record summary")
    print("=" * 70)
    print()

    for date in reversed(
        data["dates"]
    ):
        record = records[date]

        frozen = (
            not bootstrap
            and date not in active_date_set
        )

        print(
            f"{date}"
            + ("  [frozen]" if frozen else "")
        )

        if record["baseline"]:
            print(
                "  Baseline snapshot"
            )
        else:
            print(
                f"  Added ink     : "
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
        f"Current total ink: "
        f"{records[latest_date]['library_total_ink_percent']:.1f}%"
    )
    print(
        "Mutable snapshots: "
        + ", ".join(active_date_keys)
    )
    print(
        "Anchor snapshot : "
        + (
            anchor_dir.name
            if anchor_dir is not None
            else "none"
        )
    )
    print(
        f"Generated: {OUTPUT}"
    )
    print(
        f"Published PDFs: {PUBLISHED_ROOT}"
    )


if __name__ == "__main__":
    main()
