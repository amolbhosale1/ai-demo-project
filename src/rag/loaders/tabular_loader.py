"""CSV → narrative document loader with GDPR-aware field handling."""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rag.config import Settings
from rag.models import Document
from rag.privacy.fields import HIGH_SENSITIVITY_DROP, salary_band
from rag.privacy.pseudonymizer import Pseudonymizer


class TabularLoader:
    """Load HR CSV files into searchable narrative documents."""

    def __init__(self, dataset_dir: Path, settings: Settings) -> None:
        self.dataset_dir = dataset_dir
        self.settings = settings
        self.pseudo = Pseudonymizer(
            salt=settings.gdpr_pseudonym_salt,
            enabled=settings.gdpr_pseudonymize,
        )
        self._departments: dict[str, dict[str, str]] = {}
        self._locations: dict[str, dict[str, str]] = {}

    def load(self) -> list[Document]:
        self._departments = self._load_lookup("departments.csv", "department_id")
        self._locations = self._load_lookup("locations.csv", "location_id")
        docs: list[Document] = []
        docs.extend(self._load_departments())
        docs.extend(self._load_locations())
        docs.extend(self._load_employees())
        docs.extend(self._load_org_edges())
        docs.extend(self._load_promotions())
        docs.extend(self._load_salaries())
        return docs

    def _path(self, name: str) -> Path:
        return self.dataset_dir / name

    def _load_lookup(self, filename: str, key: str) -> dict[str, dict[str, str]]:
        path = self._path(filename)
        if not path.exists():
            return {}
        rows: dict[str, dict[str, str]] = {}
        with path.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                rows[row[key]] = row
        return rows

    def _ingest_meta(
        self,
        *,
        subject_id: int | None = None,
        restricted: bool = True,
        purpose: str = "hr_analytics",
        data_category: str = "workforce",
        **extra: Any,
    ) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "data_category": data_category,
            "lawful_basis": "legitimate_interest",
            "purpose": purpose,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "restricted": restricted,
        }
        if subject_id is not None:
            meta["subject_id"] = subject_id
            meta["pseudonym"] = self.pseudo.employee_label(subject_id)
        meta.update(extra)
        return meta

    def _skip_field(self, field: str) -> bool:
        if field.lower() in self.settings.excluded_fields:
            return True
        if self.settings.gdpr_sensitivity == "high" and field.lower() in HIGH_SENSITIVITY_DROP:
            return True
        return False

    def _load_departments(self) -> list[Document]:
        docs: list[Document] = []
        for row in self._departments.values():
            text = (
                f"Department '{row['department']}' (id {row['department_id']}) "
                f"belongs to category {row['category']}."
            )
            docs.append(
                Document(
                    text=text,
                    source_file="departments.csv",
                    doc_type="department",
                    metadata=self._ingest_meta(restricted=False, data_category="org_structure"),
                )
            )
        return docs

    def _load_locations(self) -> list[Document]:
        docs: list[Document] = []
        for row in self._locations.values():
            text = (
                f"Location id {row['location_id']}: {row['city']}, {row['country']} "
                f"with cost index {row['cost_index']}."
            )
            docs.append(
                Document(
                    text=text,
                    source_file="locations.csv",
                    doc_type="location",
                    metadata=self._ingest_meta(restricted=False, data_category="org_structure"),
                )
            )
        return docs

    def _load_employees(self) -> list[Document]:
        path = self._path("employees.csv")
        if not path.exists():
            return []
        docs: list[Document] = []
        with path.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                emp_id = int(row["employee_id"])
                label = self.pseudo.employee_label(emp_id)
                dept = self._departments.get(row["department_id"], {})
                loc = self._locations.get(row["location_id"], {})
                parts = [
                    f"{label} works in the "
                    f"{dept.get('department', 'Unknown')} department "
                    f"({dept.get('category', 'Unknown')} category).",
                    f"Seniority: {row['seniority']}. Work mode: {row['work_mode']}.",
                    f"Location: {loc.get('city', 'Unknown')}, {loc.get('country', 'Unknown')}.",
                ]
                if not self._skip_field("education") and "education" in row:
                    parts.append(f"Education: {row['education']}.")
                if not self._skip_field("hire_date") and "hire_date" in row:
                    parts.append(f"Hire date: {row['hire_date']}.")
                if not self._skip_field("performance_score"):
                    parts.append(f"Performance score: {row['performance_score']}.")
                if not self._skip_field("satisfaction_score"):
                    parts.append(f"Satisfaction score: {row['satisfaction_score']}.")
                if not self._skip_field("initial_salary_usd"):
                    try:
                        amount = float(row["initial_salary_usd"])
                        band = salary_band(amount)
                        if self.settings.gdpr_sensitivity == "high":
                            parts.append(f"Initial salary band: {band}.")
                        else:
                            parts.append(
                                f"Initial salary band: {band} "
                                f"(exact value retained for hr_admin purpose)."
                            )
                    except ValueError:
                        pass
                if row.get("manager_id"):
                    parts.append(
                        f"Reports to {self.pseudo.manager_label(row['manager_id'])}."
                    )
                # Never put raw name into embedded text when pseudonymizing.
                if not self.settings.gdpr_pseudonymize and not self._skip_field("name"):
                    parts.insert(0, f"Name: {row['name']}.")
                if not self._skip_field("gender") and not self.settings.gdpr_pseudonymize:
                    parts.append(f"Gender: {row['gender']}.")
                if not self._skip_field("age") and not self.settings.gdpr_pseudonymize:
                    parts.append(f"Age: {row['age']}.")

                docs.append(
                    Document(
                        text=" ".join(parts),
                        source_file="employees.csv",
                        doc_type="employee",
                        metadata=self._ingest_meta(subject_id=emp_id, restricted=True),
                    )
                )
        return docs

    def _load_org_edges(self) -> list[Document]:
        path = self._path("org_edges.csv")
        if not path.exists():
            return []
        docs: list[Document] = []
        with path.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                manager_id = int(row["source_manager_id"])
                emp_id = int(row["target_employee_id"])
                text = (
                    f"{self.pseudo.employee_label(emp_id)} reports to "
                    f"{self.pseudo.manager_label(manager_id)}."
                )
                docs.append(
                    Document(
                        text=text,
                        source_file="org_edges.csv",
                        doc_type="org_edge",
                        metadata=self._ingest_meta(subject_id=emp_id, restricted=True),
                    )
                )
        return docs

    def _load_promotions(self) -> list[Document]:
        path = self._path("promotions.csv")
        if not path.exists():
            return []
        by_emp: dict[int, list[dict[str, str]]] = defaultdict(list)
        with path.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                by_emp[int(row["employee_id"])].append(row)

        docs: list[Document] = []
        for emp_id, rows in by_emp.items():
            rows_sorted = sorted(rows, key=lambda r: r["promotion_date"])
            transitions = "; ".join(
                f"{r['from_level']}→{r['to_level']} on {r['promotion_date']}" for r in rows_sorted
            )
            text = (
                f"Promotion history for {self.pseudo.employee_label(emp_id)}: {transitions}."
            )
            docs.append(
                Document(
                    text=text,
                    source_file="promotions.csv",
                    doc_type="promotion",
                    metadata=self._ingest_meta(subject_id=emp_id, restricted=True),
                )
            )
        return docs

    def _load_salaries(self) -> list[Document]:
        path = self._path("salaries_annual.csv")
        if not path.exists():
            return []
        by_emp: dict[int, list[dict[str, str]]] = defaultdict(list)
        with path.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                by_emp[int(row["employee_id"])].append(row)

        docs: list[Document] = []
        for emp_id, rows in by_emp.items():
            latest = max(rows, key=lambda r: int(r["year"]))
            try:
                amount = float(latest["salary_usd"])
            except ValueError:
                continue
            band = salary_band(amount)
            label = self.pseudo.employee_label(emp_id)
            if self.settings.gdpr_sensitivity == "high":
                text = (
                    f"Most recent compensation for {label} in year {latest['year']} "
                    f"at seniority {latest['seniority_level']}: salary band {band}."
                )
            else:
                text = (
                    f"Most recent compensation for {label} in year {latest['year']} "
                    f"at seniority {latest['seniority_level']}: salary band {band}."
                )
            docs.append(
                Document(
                    text=text,
                    source_file="salaries_annual.csv",
                    doc_type="salary",
                    metadata=self._ingest_meta(
                        subject_id=emp_id,
                        restricted=True,
                        purpose="hr_admin",
                    ),
                )
            )
        return docs
