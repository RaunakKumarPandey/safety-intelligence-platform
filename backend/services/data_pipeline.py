"""
Safety Data Pipeline for SIH26165 (OIL Safety Intelligence Platform)
---------------------------------------------------------------------
Provides automated multi-source dataset discovery, schema normalization,
text preprocessing, hazard taxonomy alignment, deduplication, zero-leakage
train/validation/test stratification, and dataset audit statistics.

Requirements Addressed (Task 11):
1. Separates safety incident datasets from operational governance stores
   (reviews_store.json, test_reviews_store.json, alerts_store.json, actions_store.json).
2. Automatically discovers supported safety datasets: CSV, XLSX/XLS, Parquet, and validated JSON.
3. Strict normalization of descriptions, locations, sectors, worker types, accident levels, and critical risks.
4. Content-based deduplication preserving the highest severity rank on collision.
5. Ingestion validation report tracking total rows, valid rows, invalid rows, duplicates, and missing descriptions.
6. Preserves raw datasets intact (zero destructive overwrites).
"""

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
import re
import json
import unicodedata
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split


# ============================================================================
# 1. UNIFIED SAFETY REPORT SCHEMA & VALIDATION MODELS
# ============================================================================

@dataclass
class UnifiedSafetyReport:
    """Standardized schema for industrial safety observations & incidents."""
    incident_id: str
    raw_text: str
    cleaned_text: str
    severity_level: str              # Standard Roman: 'I', 'II', 'III', 'IV', 'V'
    severity_rank: int               # 1 (Minor) to 5 (Catastrophic)
    critical_risk: str               # Standardized taxonomy label
    raw_critical_risk: str           # Original label from source
    actual_accident_level: Optional[str] = None
    industry_sector: str = "Oil & Gas Operations"
    worker_type: str = "Employee (Direct)"
    gender: str = "Unknown"
    location: str = "Unknown"
    country: str = "Unknown"
    date_logged: Optional[str] = None
    source_dataset: str = "accidents.csv"
    is_synthetic: bool = False
    detected_precursors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IngestionValidationReport:
    """Audit report of the data ingestion and validation process."""
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicates: int
    missing_descriptions: int
    files_scanned: List[str]
    ignored_files: List[str]
    severity_distribution: Dict[str, int]
    quality_score_percentage: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# 2. STANDARDIZED TAXONOMY & NORMALIZATION MAPS
# ============================================================================

# Standard Severity Mapping (Maps raw strings/integers to Roman numerals I-V & rank 1-5)
SEVERITY_MAP: Dict[str, Tuple[str, int]] = {
    "i": ("I", 1),
    "1": ("I", 1),
    "minor": ("I", 1),
    "level i": ("I", 1),
    "level 1": ("I", 1),
    "ii": ("II", 2),
    "2": ("II", 2),
    "moderate": ("II", 2),
    "level ii": ("II", 2),
    "level 2": ("II", 2),
    "iii": ("III", 3),
    "3": ("III", 3),
    "serious": ("III", 3),
    "level iii": ("III", 3),
    "level 3": ("III", 3),
    "iv": ("IV", 4),
    "4": ("IV", 4),
    "critical": ("IV", 4),
    "level iv": ("IV", 4),
    "level 4": ("IV", 4),
    "v": ("V", 5),
    "5": ("V", 5),
    "catastrophic": ("V", 5),
    "fatal": ("V", 5),
    "level v": ("V", 5),
    "level 5": ("V", 5),
    "vi": ("V", 5),                 # Map single outlier Level VI to Catastrophic Level V
}

# Standard Industrial Critical Risk / Precursor Taxonomy
CRITICAL_RISK_MAP: Dict[str, str] = {
    "pressurized systems": "Pressurized Systems & Lines",
    "pressurized systems / chemical substances": "Pressurized Systems & Chemical",
    "pressed": "Pinch Points & Crushing (Pressed)",
    "manual tools": "Manual Tools & Hand Hazards",
    "chemical substances": "Chemical & Toxic Substances",
    "venomous animals": "Wildlife / Venomous Animals",
    "bees": "Wildlife / Venomous Animals",
    "cut": "Cuts, Lacerations & Sharp Edges",
    "projection": "Projected Fragments & Flying Particles",
    "projection of fragments": "Projected Fragments & Flying Particles",
    "projection/burning": "Projected Fragments & Hot Work",
    "projection/choco": "Projected Fragments & Flying Particles",
    "projection/manual tools": "Manual Tools & Hand Hazards",
    "remains of choco": "Falling Debris & Loose Material",
    "fall": "Working at Height & Fall Hazard",
    "fall prevention": "Working at Height & Fall Hazard",
    "fall prevention (same level)": "Slips, Trips & Falls (Same Level)",
    "vehicles and mobile equipment": "Vehicles & Heavy Mobile Equipment",
    "traffic": "Vehicles & Heavy Mobile Equipment",
    "suspended loads": "Lifting & Suspended Loads",
    "liquid metal": "Thermal & Hot Liquid Metal",
    "burn": "Thermal & Burn Hazards",
    "power lock": "Energy Isolation & LOTO",
    "blocking and isolation of energies": "Energy Isolation & LOTO",
    "machine protection": "Unguarded Machinery & Rotating Parts",
    "electrical shock": "Electrical Shock & High Voltage",
    "electrical installation": "Electrical Shock & High Voltage",
    "confined space": "Confined Space Entry",
    "plates": "Structural & Heavy Plates",
    "individual protection equipment": "PPE Defiance / Failure",
    "poll": "Environmental & Field Conditions",
    "others": "General Operational Hazards (Others)",
    "\\nnot applicable": "General Operational Hazards (Others)",
    "not applicable": "General Operational Hazards (Others)",
}

# Standard Industry Sector Normalization
SECTOR_MAP: Dict[str, str] = {
    "mining": "Mining & Extraction",
    "metals": "Metals & Refining",
    "others": "General Industrial",
    "oil": "Oil & Gas Operations",
    "oil & gas": "Oil & Gas Operations",
    "oil and gas": "Oil & Gas Operations",
    "petroleum": "Oil & Gas Operations",
    "drilling": "Drilling & Upstream",
    "upstream": "Drilling & Upstream",
    "production": "Production Operations",
    "refining": "Refining & Petrochemical",
    "downstream": "Refining & Petrochemical",
    "maintenance": "Maintenance & Logistics",
    "logistics": "Maintenance & Logistics",
}

# Worker Type Normalization
WORKER_MAP: Dict[str, str] = {
    "employee": "Employee (Direct)",
    "direct employee": "Employee (Direct)",
    "third party": "Contractor / Third Party",
    "third_party": "Contractor / Third Party",
    "contractor": "Contractor / Third Party",
    "third party (remote)": "Contractor / Third Party (Remote)",
}

# Operational governance JSON store filenames to strictly ignore
KNOWN_STORE_FILES = {
    "reviews_store.json",
    "test_reviews_store.json",
    "alerts_store.json",
    "actions_store.json",
}


# ============================================================================
# 3. TEXT NORMALIZATION ENGINE
# ============================================================================

class SafetyTextNormalizer:
    """Preprocesses raw field logs, fixing encoding artifacts, whitespace,
    and expanding domain acronyms while preserving critical numerical signals."""

    ACRONYM_EXPANSIONS = {
        r"\bbop\b": "blowout preventer",
        r"\blel\b": "lower explosive limit",
        r"\bscba\b": "self-contained breathing apparatus",
        r"\bppe\b": "personal protective equipment",
        r"\bloto\b": "lockout tagout",
        r"\bh2s\b": "hydrogen sulfide gas",
        r"\bptw\b": "permit to work",
        r"\bpsi\b": "psi pressure",
        r"\bbar\b": "bar pressure",
        r"\bmcc\b": "motor control center",
        r"\bvfd\b": "variable frequency drive",
    }

    @classmethod
    def clean(cls, text: Any, expand_acronyms: bool = False) -> str:
        """Cleans and standardizes raw observation text."""
        if text is None or pd.isna(text):
            return ""

        text = str(text)

        # 1. Unicode normalization (NFKD to fix Latin-1/Windows-1252 artifact letters)
        text = unicodedata.normalize("NFKD", text)

        # 2. Strip excess whitespace and linebreaks
        text = re.sub(r"[\r\n\t]+", " ", text)
        text = re.sub(r"\s{2,}", " ", text).strip()

        # 3. Optional domain acronym expansion for semantic matching
        if expand_acronyms:
            lower = text.lower()
            for pattern, replacement in cls.ACRONYM_EXPANSIONS.items():
                lower = re.sub(pattern, replacement, lower)
            text = lower

        return text


# ============================================================================
# 4. SAFETY DATA PIPELINE
# ============================================================================

class SafetyDataPipeline:
    """Full-featured safety data pipeline for discovering, normalizing,
    deduplicating, and stratifying safety incident records."""

    def __init__(self, data_dir: Optional[Union[str, Path]] = None):
        if data_dir is None:
            self.data_dir = Path(__file__).resolve().parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)

        self.normalizer = SafetyTextNormalizer()
        self.raw_records: List[Dict[str, Any]] = []
        self.unified_records: List[UnifiedSafetyReport] = []
        self.df_unified: pd.DataFrame = pd.DataFrame()
        self.validation_report: Optional[IngestionValidationReport] = None
        self.ignored_files: List[str] = []

    def is_valid_safety_dataset_file(self, file_path: Union[str, Path]) -> Tuple[bool, str]:
        """
        Validates whether a candidate file is a valid safety dataset.
        Strictly excludes operational stores (reviews_store, alerts_store, actions_store).
        """
        path = Path(file_path)
        fname = path.name.lower()

        # 1. Reject known operational stores or files ending in _store.json
        if fname in KNOWN_STORE_FILES or fname.endswith("_store.json") or fname.endswith("store.json"):
            return False, f"Operational governance store file ({fname}) excluded."

        # 2. Supported extensions
        if path.suffix not in [".csv", ".xlsx", ".xls", ".parquet", ".json"]:
            return False, f"Unsupported file extension '{path.suffix}'."

        # 3. JSON content validation
        if path.suffix == ".json":
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = json.load(f)

                if isinstance(content, dict):
                    # Check if keys look like store IDs (REV-, ALT-, ACT-)
                    sample_keys = list(content.keys())[:5]
                    if sample_keys and any(k.startswith(("REV-", "ALT-", "ACT-")) for k in sample_keys):
                        return False, "Operational ID-keyed JSON store excluded."

                    # If it's a dict wrapping a report list: e.g. {"reports": [...]} or {"data": [...]}
                    for wrap_key in ["reports", "data", "incidents", "records"]:
                        if wrap_key in content and isinstance(content[wrap_key], list):
                            content = content[wrap_key]
                            break

                if not isinstance(content, list):
                    return False, "JSON dataset must be a list of records."

                if len(content) == 0:
                    return False, "JSON dataset is empty."

                # Verify at least one record contains a safety text/description field
                first_rec = content[0]
                if not isinstance(first_rec, dict):
                    return False, "JSON records must be JSON objects."

                desc_keys = {"Description", "description", "narrative", "report_text", "text", "Observation"}
                if not any(k in first_rec for k in desc_keys):
                    return False, "JSON dataset records lack safety description fields."

            except Exception as e:
                return False, f"Failed to parse JSON safety dataset: {e}"

        return True, "Valid safety incident dataset."

    def discover_datasets(self) -> List[Path]:
        """
        Discovers all valid CSV, XLSX, Parquet, and JSON safety datasets in data directory.
        Excludes operational review, alert, and action stores.
        """
        if not self.data_dir.exists():
            return []

        candidate_files: List[Path] = []
        for ext in ["*.csv", "*.xlsx", "*.xls", "*.parquet", "*.json"]:
            candidate_files.extend(list(self.data_dir.glob(ext)))

        valid_files: List[Path] = []
        self.ignored_files = []

        for fpath in candidate_files:
            is_valid, reason = self.is_valid_safety_dataset_file(fpath)
            if is_valid:
                valid_files.append(fpath)
            else:
                self.ignored_files.append(f"{fpath.name} ({reason})")

        return sorted(valid_files)

    def load_raw_dataset(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """Safely loads a tabular or JSON dataset file with fallback encoding detection."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {path}")

        if path.suffix == ".csv":
            try:
                df = pd.read_csv(path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(path, encoding="latin-1")
        elif path.suffix in [".xlsx", ".xls"]:
            df = pd.read_excel(path)
        elif path.suffix == ".parquet":
            df = pd.read_parquet(path)
        elif path.suffix == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for k in ["reports", "data", "incidents", "records"]:
                    if k in data and isinstance(data[k], list):
                        data = data[k]
                        break
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = pd.read_json(path)
        else:
            raise ValueError(f"Unsupported dataset format: {path.suffix}")

        return df

    def normalize_record(
        self,
        row: pd.Series,
        source_name: str,
        index_num: int
    ) -> Optional[UnifiedSafetyReport]:
        """
        Maps a raw heterogeneous dataframe row to the UnifiedSafetyReport schema
        with comprehensive normalization of descriptions, locations, sectors,
        worker types, accident levels, and critical risks.
        """
        # 1. Extract and normalize raw description text
        raw_text = None
        for col in ["Description", "description", "narrative", "report_text", "text", "Observation", "Incident Description"]:
            if col in row and pd.notna(row[col]) and str(row[col]).strip():
                raw_text = str(row[col])
                break

        if not raw_text or len(raw_text.strip()) < 5:
            # Drop empty or uninformative records
            return None

        cleaned_text = self.normalizer.clean(raw_text)

        # 2. Extract and normalize incident ID
        raw_id = None
        for col in ["Unnamed: 0", "incident_id", "id", "ID", "Report ID", "index"]:
            if col in row and pd.notna(row[col]):
                raw_id = str(row[col])
                break
        incident_id = f"{source_name}:{raw_id if raw_id is not None else index_num}"

        # 3. Extract and normalize Potential Severity Level
        raw_severity = None
        for col in ["Potential Accident Level", "potential_accident_level", "potential_severity", "severity", "Severity", "level", "Potential Level"]:
            if col in row and pd.notna(row[col]):
                raw_severity = str(row[col]).strip()
                break

        sev_key = str(raw_severity).lower().strip() if raw_severity else "i"
        severity_level, severity_rank = SEVERITY_MAP.get(sev_key, ("I", 1))

        # 4. Actual Accident Level (Consequence)
        actual_level = None
        for col in ["Accident Level", "accident_level", "actual_level", "actual_severity", "Consequence"]:
            if col in row and pd.notna(row[col]):
                act_key = str(row[col]).strip().lower()
                actual_level, _ = SEVERITY_MAP.get(act_key, (str(row[col]).strip(), 1))
                break

        # 5. Extract and normalize Critical Risk / Precursor
        raw_risk = "Others"
        for col in ["Critical Risk", "critical_risk", "hazard", "Hazard Type", "precursor", "Risk Category"]:
            if col in row and pd.notna(row[col]):
                raw_risk = str(row[col]).strip()
                break

        risk_clean_key = raw_risk.lower().strip()
        critical_risk = CRITICAL_RISK_MAP.get(risk_clean_key, raw_risk)

        # 6. Normalize Location
        raw_location = "Unknown"
        for col in ["Local", "location", "Location", "site", "Site", "Plant", "Facility"]:
            if col in row and pd.notna(row[col]) and str(row[col]).strip():
                raw_location = str(row[col]).strip()
                break
        location = raw_location if raw_location not in ["nan", "None", ""] else "Unknown"

        # 7. Normalize Sector & Department
        raw_sector = "Others"
        for col in ["Industry Sector", "industry_sector", "sector", "Sector", "Department", "department"]:
            if col in row and pd.notna(row[col]) and str(row[col]).strip():
                raw_sector = str(row[col]).strip()
                break
        sector_clean_key = raw_sector.lower().strip()
        sector = SECTOR_MAP.get(sector_clean_key, raw_sector.title() if raw_sector else "General Industrial")

        # 8. Normalize Worker Type
        raw_worker = "Employee"
        for col in ["Employee or Third Party", "worker_type", "Worker Type", "employee_type", "contractor_type"]:
            if col in row and pd.notna(row[col]) and str(row[col]).strip():
                raw_worker = str(row[col]).strip()
                break
        worker_clean_key = raw_worker.lower().strip()
        worker = WORKER_MAP.get(worker_clean_key, "Employee (Direct)")

        # 9. Normalize Gender, Country, Date
        raw_gender = str(row.get("Genre", row.get("Gender", "Unknown"))).strip().capitalize()
        gender = raw_gender if raw_gender in ["Male", "Female"] else "Unknown"

        country = str(row.get("Countries", row.get("country", "Unknown"))).strip()
        if country in ["nan", "None", ""]:
            country = "Unknown"

        date_val = str(row.get("Data", row.get("date", "Unknown"))).strip()
        if date_val in ["nan", "None", ""]:
            date_val = "Unknown"

        return UnifiedSafetyReport(
            incident_id=incident_id,
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            severity_level=severity_level,
            severity_rank=severity_rank,
            critical_risk=critical_risk,
            raw_critical_risk=raw_risk,
            actual_accident_level=actual_level,
            industry_sector=sector,
            worker_type=worker,
            gender=gender,
            location=location,
            country=country,
            date_logged=date_val,
            source_dataset=source_name,
            is_synthetic=False
        )

    def process_all(self, deduplicate: bool = True) -> pd.DataFrame:
        """
        Discovers, loads, normalizes, deduplicates, and packages all datasets
        into a clean DataFrame, generating a complete IngestionValidationReport.
        """
        dataset_files = self.discover_datasets()
        if not dataset_files:
            raise FileNotFoundError(f"No valid dataset files found in {self.data_dir}")

        all_reports: List[UnifiedSafetyReport] = []
        total_rows_scanned = 0
        missing_descriptions_count = 0
        invalid_rows_count = 0
        files_scanned = [f.name for f in dataset_files]

        for fpath in dataset_files:
            source_name = fpath.name
            df_raw = self.load_raw_dataset(fpath)
            total_rows_scanned += len(df_raw)

            for idx, row in df_raw.iterrows():
                # Check for description presence
                has_desc = False
                for col in ["Description", "description", "narrative", "report_text", "text", "Observation"]:
                    if col in row and pd.notna(row[col]) and len(str(row[col]).strip()) >= 5:
                        has_desc = True
                        break

                if not has_desc:
                    missing_descriptions_count += 1
                    invalid_rows_count += 1
                    continue

                report = self.normalize_record(row, source_name=source_name, index_num=idx)
                if report:
                    all_reports.append(report)
                else:
                    invalid_rows_count += 1

        # Convert to DataFrame
        records_dict = [r.to_dict() for r in all_reports]
        df = pd.DataFrame(records_dict)

        raw_parsed_count = len(df)
        duplicates_count = 0

        if deduplicate and not df.empty:
            # Content-based deduplication on cleaned text
            # When duplicate text exists, preserve the record with the HIGHEST severity rank
            # (conservative safety rule: higher consequence potential dominates)
            df = df.sort_values("severity_rank", ascending=False)
            initial_count = len(df)
            df = df.drop_duplicates(subset=["cleaned_text"], keep="first").reset_index(drop=True)
            duplicates_count = initial_count - len(df)

        self.df_unified = df

        # Generate IngestionValidationReport
        sev_counts = df["severity_level"].value_counts().to_dict() if not df.empty else {}
        quality_score = round((len(df) / total_rows_scanned) * 100, 2) if total_rows_scanned > 0 else 0.0

        self.validation_report = IngestionValidationReport(
            total_rows=total_rows_scanned,
            valid_rows=len(df),
            invalid_rows=invalid_rows_count,
            duplicates=duplicates_count,
            missing_descriptions=missing_descriptions_count,
            files_scanned=files_scanned,
            ignored_files=self.ignored_files,
            severity_distribution=sev_counts,
            quality_score_percentage=quality_score
        )

        return df

    def get_validation_report(self) -> Dict[str, Any]:
        """Returns the ingestion audit report."""
        if self.validation_report is None or self.df_unified.empty:
            self.process_all(deduplicate=True)
        return self.validation_report.to_dict()

    def get_dataset_statistics(self) -> Dict[str, Any]:
        """Computes comprehensive dataset quality, distribution, and split statistics."""
        if self.df_unified.empty:
            self.process_all(deduplicate=False)

        df = self.df_unified

        total_records = len(df)
        unique_texts = df["cleaned_text"].nunique()
        duplicate_count = total_records - unique_texts

        sev_dist = df["severity_level"].value_counts().to_dict()
        risk_dist = df["critical_risk"].value_counts().head(10).to_dict()
        sector_dist = df["industry_sector"].value_counts().to_dict()
        worker_dist = df["worker_type"].value_counts().to_dict()
        loc_dist = df["location"].value_counts().head(10).to_dict()

        return {
            "total_records": total_records,
            "unique_records": unique_texts,
            "duplicate_count": duplicate_count,
            "severity_distribution": sev_dist,
            "top_critical_risks": risk_dist,
            "sector_distribution": sector_dist,
            "worker_distribution": worker_dist,
            "location_distribution": loc_dist,
            "missing_values": {col: int(df[col].isnull().sum()) for col in df.columns},
            "validation_report": self.get_validation_report()
        }

    def create_stratified_splits(
        self,
        test_size: float = 0.15,
        val_size: float = 0.15,
        random_state: int = 42
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Creates zero-leakage, stratified Train, Validation, and Test partitions."""
        if self.df_unified.empty:
            self.process_all(deduplicate=True)

        df = self.df_unified.copy()

        # Target label for stratification
        y = df["severity_level"]

        # 1. First Split: Train+Val vs Test
        train_val_df, test_df = train_test_split(
            df,
            test_size=test_size,
            random_state=random_state,
            stratify=y
        )

        # 2. Second Split: Train vs Val (adjusted ratio)
        val_ratio_adjusted = val_size / (1.0 - test_size)
        train_df, val_df = train_test_split(
            train_val_df,
            test_size=val_ratio_adjusted,
            random_state=random_state,
            stratify=train_val_df["severity_level"]
        )

        return (
            train_df.reset_index(drop=True),
            val_df.reset_index(drop=True),
            test_df.reset_index(drop=True)
        )


# ============================================================================
# 5. CONVENIENCE RUNNER
# ============================================================================

def get_processed_safety_data(deduplicate: bool = True) -> pd.DataFrame:
    """Convenience helper to retrieve normalized safety dataset."""
    pipeline = SafetyDataPipeline()
    return pipeline.process_all(deduplicate=deduplicate)


if __name__ == "__main__":
    pipeline = SafetyDataPipeline()
    df = pipeline.process_all(deduplicate=True)
    report = pipeline.get_validation_report()
    stats = pipeline.get_dataset_statistics()

    print("=" * 65)
    print("      SIH26165 SAFETY DATA INGESTION & VALIDATION AUDIT")
    print("=" * 65)
    print(f"Total Rows Scanned:     {report['total_rows']}")
    print(f"Valid Usable Records:   {report['valid_rows']}")
    print(f"Duplicates Pruned:      {report['duplicates']}")
    print(f"Missing Descriptions:   {report['missing_descriptions']}")
    print(f"Quality Score:          {report['quality_score_percentage']}%")
    print(f"Files Ingested:         {', '.join(report['files_scanned'])}")
    print(f"Files Excluded/Ignored: {', '.join(report['ignored_files'])}")
    print("\nNormalized Severity Distribution (I to V):")
    for k, v in sorted(report['severity_distribution'].items()):
        print(f"  Level {k}: {v} reports ({v/report['valid_rows']*100:.1f}%)")

    train_df, val_df, test_df = pipeline.create_stratified_splits()
    print("\nStratified Partitions:")
    print(f"  Training Set:   {len(train_df)} rows ({len(train_df)/len(df)*100:.1f}%)")
    print(f"  Validation Set: {len(val_df)} rows ({len(val_df)/len(df)*100:.1f}%)")
    print(f"  Test Set:       {len(test_df)} rows ({len(test_df)/len(df)*100:.1f}%)")
    print("=" * 65)
