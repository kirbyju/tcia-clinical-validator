import json
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any
import pandas as pd
import zipfile
import hashlib
import numpy as np


# ============================================================
# Data Inventory & Standardization: Medical Imaging (DICOM)
# ============================================================

class DataInventoryStandardizer:
    def __init__(self):
        self.inventory = {}
        self.standard_columns = [
            "PatientID",
            "StudyInstanceUID",
            "SeriesInstanceUID",
            "StudyDate",
            "StudyDescription",
            "SeriesDescription",
            "Modality",
            "Manufacturer",
            "ManufacturerModelName",
            "BodyPartExamined",
            "SliceThickness",
            "PixelSpacing",
            "Rows",
            "Columns",
            "PatientAge",
            "PatientSex"
        ]
        self.nifti_columns = [
            "PatientID",
            "FileName",
            "FilePath",
            "Modality",
            "DimX",
            "DimY",
            "DimZ",
            "SpacingX",
            "SpacingY",
            "SpacingZ",
            "DataType",
            "NumVoxels",
            "FileSizeMB"
        ]

    def analyze_directory(self, root_path: str, zip_per_series: bool = False):
        root_path = Path(root_path)
        if not root_path.exists():
            raise ValueError(f"Directory does not exist: {root_path}")

        print("Starting data inventory...")

        self.inventory = {
            "dataset_overview": self._dataset_overview(root_path),
            "file_format_inventory": self._file_format_inventory(root_path),
            "dicom_summary": self._dicom_summary(root_path),
            "nifti_summary": self._nifti_summary(root_path)
        }

        self.extract_dicom_series_metadata(
            root_path=root_path,
            output_tsv="dicom_series_inventory.tsv",
            zip_per_series=zip_per_series
        )

        self.extract_nifti_metadata(
            root_path=root_path,
            output_tsv="nifti_series_inventory.tsv"
        )

        # NEW: Generate Master Data Dictionary for all spreadsheets found
        self.generate_master_data_dictionary(root_path)

        return self.inventory

    # --------------------------------------------------------
    # FEATURE REQUEST: Master Data Dictionary Template
    # --------------------------------------------------------
    def generate_master_data_dictionary(self, root_path: Path, output_tsv: str = "master_data_dictionary.tsv"):
        """
        Finds all spreadsheets and creates a data dictionary template.
        """
        print("Generating Master Data Dictionary template...")
        extensions = ['.csv', '.tsv', '.xlsx', '.xls']
        dict_rows = []

        # Find all files with matching extensions
        files_to_process = []
        for ext in extensions:
            files_to_process.extend(list(root_path.rglob(f"*{ext}")))

        for file_path in files_to_process:
            try:
                # Determine loading method based on extension
                if file_path.suffix.lower() == '.csv':
                    df = pd.read_csv(file_path)
                elif file_path.suffix.lower() == '.tsv':
                    df = pd.read_csv(file_path, sep='\t')
                else:  # Excel
                    df = pd.read_excel(file_path)

                # Clean DF: drop empty columns/rows to avoid noise in dictionary
                df = df.dropna(how='all').dropna(axis=1, how='all')

                for col in df.columns:
                    # Get unique values, drop NaNs, limit to first 10 for summary
                    unique_vals = df[col].dropna().unique()
                    val_summary = ", ".join(map(str, unique_vals[:10]))
                    if len(unique_vals) > 10:
                        val_summary += ", ..."

                    dict_rows.append({
                        "Data Element Name": f"{file_path}\\{col}",
                        "Data Element Values": val_summary,
                        "Common Data Element ID": "",  # Placeholder
                        "Data Element Definition": ""  # Placeholder
                    })
            except Exception as e:
                print(f"  Skipping {file_path.name} due to error: {e}")

        if dict_rows:
            dictionary_df = pd.DataFrame(dict_rows)
            dictionary_df.to_csv(output_tsv, sep='\t', index=False)
            print(f"✔ Master Data Dictionary written to {output_tsv}")
        else:
            print("  No spreadsheets found to generate a data dictionary.")

    # -------------------------------
    # Dataset inventory
    # -------------------------------

    def _dataset_overview(self, root_path: Path) -> Dict[str, Any]:
        total_size = 0
        total_files = 0

        for f in root_path.rglob("*"):
            if f.is_file():
                total_files += 1
                total_size += f.stat().st_size

        return {
            "total_files": total_files,
            "total_size_gb": round(total_size / (1024 ** 3), 2),
            "analysis_timestamp": pd.Timestamp.now().isoformat()
        }

    def _file_format_inventory(self, root_path: Path) -> Dict[str, Any]:
        formats = defaultdict(lambda: {"count": 0, "size_bytes": 0})

        for f in root_path.rglob("*"):
            if f.is_file():
                ext = f.suffix.lower() if f.suffix else "no_extension"
                formats[ext]["count"] += 1
                formats[ext]["size_bytes"] += f.stat().st_size

        return {
            ext: {
                "file_count": info["count"],
                "total_size_gb": round(info["size_bytes"] / (1024 ** 3), 4)
            }
            for ext, info in formats.items()
        }

    # -------------------------------
    # DICOM inventory (high level)
    # -------------------------------

    def _dicom_summary(self, root_path: Path) -> Dict[str, Any]:
        try:
            import pydicom
        except ImportError:
            return {"error": "pydicom not installed"}

        dicom_files = list(root_path.rglob("*.dcm")) + list(root_path.rglob("*.dicom"))

        return {
            "dicom_file_count": len(dicom_files)
        }

    #--------------------------------
    # NIFTI inventory
    #--------------------------------

    def _nifti_summary(self, root_path: Path) -> Dict[str, Any]:
        nifti_files = list(root_path.rglob("*.nii")) + \
                      list(root_path.rglob("*.nii.gz"))

        return {
            "nifti_file_count": len(nifti_files)
        }

    #--------------------------------
    # NIFTI metadata extraction
    # -------------------------------

    def extract_nifti_metadata(
            self,
            root_path: Path,
            output_tsv: str = "nifti_series_inventory.tsv"
    ):
        try:
            import nibabel as nib
        except ImportError:
            raise RuntimeError("nibabel is required. Run: pip install nibabel")

        nifti_files = list(root_path.rglob("*.nii")) + \
                      list(root_path.rglob("*.nii.gz"))

        if not nifti_files:
            print("No NIfTI files found.")
            return

        print(f"Extracting metadata from {len(nifti_files)} NIfTI files...")

        rows = []

        for i, path in enumerate(nifti_files):
            if i % 50 == 0:
                print(f"  Processed {i}/{len(nifti_files)}")

            try:
                img = nib.load(str(path))
                header = img.header

                # BraTS-style grouping
                patient_id = ""
                modality = ""

                rows.append({
                    "PatientID": patient_id,
                    "FileName": path.name,
                    "FilePath": str(path),
                    "Modality": modality,

                    "DimX": img.shape[0],
                    "DimY": img.shape[1],
                    "DimZ": img.shape[2] if len(img.shape) > 2 else "",

                    "SpacingX": header.get_zooms()[0],
                    "SpacingY": header.get_zooms()[1],
                    "SpacingZ": header.get_zooms()[2] if len(header.get_zooms()) > 2 else "",

                    "DataType": str(header.get_data_dtype()),
                    "NumVoxels": int(np.prod(img.shape)),
                    "FileSizeMB": round(path.stat().st_size / (1024 ** 2), 3),

                    # fields that only DICOM usually has
                    "Manufacturer": "",
                    "ManufacturerModelName": "",
                    "StudyDate": "",
                    "StudyDescription": "",
                    "SeriesDescription": "",
                    "SeriesInstanceUID": "",
                    "StudyInstanceUID": ""
                })

            except Exception:
                continue

        if not rows:
            print("No NIfTI metadata extracted. TSV not created.")
            return

        df = pd.DataFrame(rows)

        for col in self.standard_columns:
            if col not in df.columns:
                df[col] = ""

        df = df[self.nifti_columns]

        df.sort_values(by=["PatientID", "Modality"], inplace=True, ignore_index=True)

        df.to_csv(output_tsv, sep="\t", index=False)

        print(f"✔ NIfTI series-level TSV written to {output_tsv}")

    # -------------------------------
    # DICOM metadata extraction
    # -------------------------------

    def extract_dicom_series_metadata(
            self,
            root_path: Path,
            output_tsv: str,
            zip_per_series: bool = False
    ):
        try:
            import pydicom
            from pydicom.errors import InvalidDicomError
        except ImportError:
            raise RuntimeError("pydicom is required")

        dicom_files = list(root_path.rglob("*.dcm")) + list(root_path.rglob("*.dicom"))
        if not dicom_files:
            print("No DICOM files found.")
            return

        print(f"Extracting metadata from {len(dicom_files)} DICOM files...")

        series_index = {}
        series_files = defaultdict(list)
        slice_thickness_map = defaultdict(set)
        pixel_spacing_map = defaultdict(set)
        zip_md5_map = {}

        for i, path in enumerate(dicom_files):
            if i % 100 == 0:
                print(f"  Processed {i}/{len(dicom_files)}")

            try:
                ds = pydicom.dcmread(path, stop_before_pixels=True)
                series_uid = self._safe_get(ds, "SeriesInstanceUID")
                if not series_uid:
                    continue

                series_files[series_uid].append(path)

                if hasattr(ds, "SliceThickness"):
                    try:
                        slice_thickness_map[series_uid].add(float(ds.SliceThickness))
                    except Exception:
                        pass

                if hasattr(ds, "PixelSpacing"):
                    try:
                        spacing = tuple(float(x) for x in ds.PixelSpacing)
                        pixel_spacing_map[series_uid].add(spacing)
                    except Exception:
                        pass

                if series_uid not in series_index:
                    series_index[series_uid] = {
                        "PatientID": self._safe_get(ds, "PatientID"),
                        "StudyInstanceUID": self._safe_get(ds, "StudyInstanceUID"),
                        "StudyDate": self._safe_get(ds, "StudyDate"),
                        "StudyDescription": self._safe_get(ds, "StudyDescription"),

                        "SeriesInstanceUID": series_uid,
                        "SeriesDescription": self._safe_get(ds, "SeriesDescription"),

                        "Modality": self._safe_get(ds, "Modality"),
                        "BodyPartExamined": self._safe_get(ds, "BodyPartExamined"),

                        "Manufacturer": self._safe_get(ds, "Manufacturer"),
                        "ManufacturerModelName": self._safe_get(ds, "ManufacturerModelName"),

                        # Additional useful metadata
                        "InstitutionName": self._safe_get(ds, "InstitutionName"),
                        "StationName": self._safe_get(ds, "StationName"),
                        "SeriesNumber": self._safe_get(ds, "SeriesNumber"),
                        "StudyID": self._safe_get(ds, "StudyID"),

                        "PatientAge": self._safe_get(ds, "PatientAge"),
                        "PatientSex": self._safe_get(ds, "PatientSex"),

                        "Rows": self._safe_get(ds, "Rows"),
                        "Columns": self._safe_get(ds, "Columns"),

                        "SliceThickness": self._safe_get(ds, "SliceThickness"),
                        "PixelSpacing": self._safe_get(ds, "PixelSpacing"),

                        "ImageOrientationPatient": self._safe_get(ds, "ImageOrientationPatient"),
                        "ImagePositionPatient": self._safe_get(ds, "ImagePositionPatient")
                    }

            except (InvalidDicomError, Exception):
                continue

        if zip_per_series:
            zip_dir = Path("zips")
            zip_dir.mkdir(exist_ok=True)
            print("Creating ZIP files per SeriesInstanceUID...")
            for series_uid, files in series_files.items():
                zip_path = zip_dir / f"{series_uid}.zip"
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for f in files:
                        zf.write(f, arcname=f.name)
                md5 = hashlib.md5()
                with open(zip_path, "rb") as fh:
                    for chunk in iter(lambda: fh.read(8192), b""):
                        md5.update(chunk)
                zip_md5_map[series_uid] = md5.hexdigest()

        rows = []
        for series_uid, base in series_index.items():
            row = base.copy()


            # Keep your existing metadata

            row["SliceThickness"] = sorted(slice_thickness_map.get(series_uid, []))
            row["PixelSpacing"] = sorted(pixel_spacing_map.get(series_uid, []))
            if zip_per_series:
                row["ZipMD5"] = zip_md5_map.get(series_uid)
            rows.append(row)

        if not rows:
            print("No DICOM metadata extracted. TSV not created.")
            return

        df = pd.DataFrame(rows)

        for col in self.standard_columns:
            if col not in df.columns:
                df[col] = ""

        df = df[self.standard_columns]
        df.sort_values(by=["PatientID", "StudyInstanceUID", "SeriesInstanceUID"], inplace=True, ignore_index=True)
        df.to_csv(output_tsv, sep="\t", index=False)
        print(f"✔ Series-level TSV written to {output_tsv}")

    def _safe_get(self, ds, attr: str) -> str:
        return str(getattr(ds, attr, "")).strip()

    def save_inventory(self, output_json="data_inventory.json"):
        with open(output_json, "w") as f:
            json.dump(self.inventory, f, indent=2)
        print(f"✔ Inventory JSON written to {output_json}")


# ============================================================
# CLI ENTRY POINT
# ============================================================

if __name__ == "__main__":
    analyzer = DataInventoryStandardizer()

    folder = input("Enter path to data directory (blank = current): ").strip()
    if not folder:
        folder = "."

    zip_choice = input("Create one ZIP per DICOM Series? (y/n): ").strip().lower()
    zip_per_series = zip_choice == "y"

    analyzer.analyze_directory(folder, zip_per_series=zip_per_series)
    analyzer.save_inventory()

    print("\nData Inventory & Standardization complete.")