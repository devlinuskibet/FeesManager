"""
Bulk import service for students and guardians.

Supports CSV (.csv) and Excel (.xlsx) files. Works in two modes:

* dry_run=True  — validate every row, return a row-level report, write nothing.
* dry_run=False — validate, then commit all valid rows in a single database
  transaction. Invalid rows are reported but do not block valid ones.

Expected column headers (case-insensitive, whitespace-trimmed):

student_admission_number, student_first_name, student_last_name,
class_stream_level, class_stream_stream, student_status, student_date_admitted,
guardian_name, guardian_phone, guardian_relationship, guardian_is_primary

One row = one student + one guardian link. A student may appear on multiple
rows (each with a different guardian); guardians are matched by phone within
the school, created if absent.
"""

import csv
import io
import re
from datetime import date

from django.db import transaction

try:
    import openpyxl
except ImportError:  # pragma: no cover - openpyxl optional until Excel import used
    openpyxl = None

from apps.academics.models import ClassStream
from apps.students.models import Guardian, Student, StudentGuardian

VALID_STATUSES = {"active", "transferred", "graduated", "suspended"}
BOOLEAN_TRUE = {"1", "true", "yes", "y", "t"}


def _normalize_admission_number(value):
    if value is None:
        return ""
    return re.sub(r"\s+", "", str(value).strip()).upper()


def _parse_bool(value):
    if value is None:
        return False
    return str(value).strip().lower() in BOOLEAN_TRUE


def _parse_date(value):
    """Accept YYYY-MM-DD or a datetime.date."""
    if value is None or str(value).strip() == "":
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    # strptime produces a naive datetime, but we immediately call .date() so
    # timezone awareness is irrelevant here.
    try:
        from datetime import datetime

        return datetime.strptime(text, "%Y-%m-%d").date()  # noqa: DTZ007
    except ValueError:
        return None


def _read_rows(uploaded_file):
    """Yield dict rows from a CSV or Excel file-like object."""
    name = uploaded_file.name.lower()
    raw = uploaded_file.read()

    if name.endswith(".csv"):
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            yield {_clean_key(k): v for k, v in row.items()}

    elif name.endswith((".xlsx", ".xls")):
        if openpyxl is None:
            raise ImportError("openpyxl is required for Excel import")  # noqa: TRY003
        wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return
        headers = [_clean_key(h) for h in rows[0]]
        for row in rows[1:]:
            if all(v is None for v in row):
                continue
            yield dict(zip(headers, row, strict=False))

    else:
        raise ValueError("Unsupported file type. Upload .csv or .xlsx.")  # noqa: TRY003


def _clean_key(key):
    if key is None:
        return ""
    return re.sub(r"\s+", "", str(key).strip().lower())


def import_students(uploaded_file, school, dry_run=True, user=None):
    """Import students/guardians from an uploaded file."""
    report = {
        "status": "ok",
        "dry_run": dry_run,
        "total_rows": 0,
        "valid_rows": 0,
        "invalid_rows": 0,
        "created_students": 0,
        "created_guardians": 0,
        "created_links": 0,
        "rows": [],
        "duplicate_admission_numbers": [],
    }

    try:
        rows = list(_read_rows(uploaded_file))
    except Exception as exc:  # noqa: BLE001
        report["status"] = "has_errors"
        report["rows"] = [
            {
                "row_number": 0,
                "status": "error",
                "errors": [f"Could not read file: {exc}"],
                "student": None,
                "guardian": None,
            }
        ]
        return report

    report["total_rows"] = len(rows)

    existing_admission_numbers = set(Student.objects.for_school(school).values_list("admission_number", flat=True))
    class_streams = {(cs.level, cs.stream or ""): cs for cs in ClassStream.objects.for_school(school)}
    guardians_by_phone = {g.phone: g for g in Guardian.objects.for_school(school)}

    seen_in_file = set()
    valid_entries = []

    for idx, raw_row in enumerate(rows, start=2):
        row_number = idx
        errors = []

        admission_number = _normalize_admission_number(raw_row.get("student_admission_number"))
        first_name = (raw_row.get("student_first_name") or "").strip()
        last_name = (raw_row.get("student_last_name") or "").strip()
        class_level = (raw_row.get("class_stream_level") or "").strip()
        class_stream_name = (raw_row.get("class_stream_stream") or "").strip()
        status = (raw_row.get("student_status") or "active").strip().lower()
        date_admitted = _parse_date(raw_row.get("student_date_admitted"))

        guardian_name = (raw_row.get("guardian_name") or "").strip()
        guardian_phone = (raw_row.get("guardian_phone") or "").strip()
        guardian_relationship = (raw_row.get("guardian_relationship") or "guardian").strip().lower()
        guardian_is_primary = _parse_bool(raw_row.get("guardian_is_primary"))

        if not admission_number:
            errors.append("student_admission_number is required.")
        if not first_name:
            errors.append("student_first_name is required.")
        if not last_name:
            errors.append("student_last_name is required.")
        if status not in VALID_STATUSES:
            errors.append(f"student_status must be one of {sorted(VALID_STATUSES)}.")
        if date_admitted is None:
            errors.append("student_date_admitted is required (YYYY-MM-DD).")

        class_stream_obj = None
        if class_level:
            key = (class_level, class_stream_name)
            class_stream_obj = class_streams.get(key)
            if class_stream_obj is None:
                errors.append(
                    f"Class/stream '{class_level} {class_stream_name}' not found for this school and academic year."
                )

        guardian_obj = None
        if guardian_name or guardian_phone:
            if not guardian_name:
                errors.append("guardian_name is required when guardian_phone is given.")
            if not guardian_phone:
                errors.append("guardian_phone is required when guardian_name is given.")
            if guardian_phone and guardian_name:
                if not re.match(r"^\+?[1-9]\d{1,14}$", guardian_phone):
                    errors.append("guardian_phone must be E.164, e.g. +254712345678.")
                else:
                    guardian_obj = guardians_by_phone.get(guardian_phone)

        if admission_number:
            if admission_number in seen_in_file:
                errors.append(f"Duplicate admission number '{admission_number}' within file.")
                report["duplicate_admission_numbers"].append(admission_number)
            elif admission_number in existing_admission_numbers:
                errors.append(f"Admission number '{admission_number}' already exists.")
                report["duplicate_admission_numbers"].append(admission_number)
            else:
                seen_in_file.add(admission_number)

        row_result = {
            "row_number": row_number,
            "status": "invalid" if errors else "valid",
            "errors": errors,
            "student": None,
            "guardian": None,
        }

        if not errors:
            report["valid_rows"] += 1
            valid_entries.append(
                {
                    "row_number": row_number,
                    "admission_number": admission_number,
                    "first_name": first_name,
                    "last_name": last_name,
                    "class_stream": class_stream_obj,
                    "status": status,
                    "date_admitted": date_admitted,
                    "guardian_name": guardian_name,
                    "guardian_phone": guardian_phone,
                    "guardian_relationship": guardian_relationship,
                    "guardian_is_primary": guardian_is_primary,
                    "guardian_obj": guardian_obj,
                }
            )
            row_result["student"] = admission_number
            row_result["guardian"] = guardian_phone or None
        else:
            report["invalid_rows"] += 1
            report["status"] = "has_errors"

        report["rows"].append(row_result)

    # --- Commit (unless dry run) ---
    if not dry_run and report["valid_rows"] > 0:
        try:
            with transaction.atomic():
                created_students = 0
                created_guardians = 0
                created_links = 0

                for entry in valid_entries:
                    student, s_created = Student.objects.update_or_create(
                        school=school,
                        admission_number=entry["admission_number"],
                        defaults={
                            "first_name": entry["first_name"],
                            "last_name": entry["last_name"],
                            "class_stream": entry["class_stream"],
                            "status": entry["status"],
                            "date_admitted": entry["date_admitted"],
                        },
                    )
                    if s_created:
                        created_students += 1

                    guardian = entry["guardian_obj"]
                    if guardian is None and entry["guardian_phone"]:
                        guardian, g_created = Guardian.objects.update_or_create(
                            school=school,
                            phone=entry["guardian_phone"],
                            defaults={
                                "name": entry["guardian_name"],
                                "relationship": entry["guardian_relationship"],
                                "is_primary": entry["guardian_is_primary"],
                            },
                        )
                        if g_created:
                            created_guardians += 1
                    elif guardian is not None:
                        updated = False
                        if entry["guardian_name"] and guardian.name != entry["guardian_name"]:
                            guardian.name = entry["guardian_name"]
                            updated = True
                        if entry["guardian_relationship"] and guardian.relationship != entry["guardian_relationship"]:
                            guardian.relationship = entry["guardian_relationship"]
                            updated = True
                        if updated:
                            guardian.save()

                    if guardian:
                        link, l_created = StudentGuardian.objects.update_or_create(
                            school=school,
                            student=student,
                            guardian=guardian,
                            defaults={
                                "is_primary": entry["guardian_is_primary"],
                                "relationship": entry["guardian_relationship"],
                            },
                        )
                        if l_created:
                            created_links += 1

                report["created_students"] = created_students
                report["created_guardians"] = created_guardians
                report["created_links"] = created_links
                report["status"] = "ok"

        except Exception as exc:  # noqa: BLE001
            report["status"] = "has_errors"
            report["rows"].append(
                {
                    "row_number": 0,
                    "status": "error",
                    "errors": [f"Commit failed: {exc}"],
                    "student": None,
                    "guardian": None,
                }
            )

    return report
