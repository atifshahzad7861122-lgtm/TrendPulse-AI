"""Standalone Multi-Format Data Exporter for Scraped Product Intelligence and Reviews."""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from app.core.logging import logger


class DataExporter:
    """Production-grade multi-format exporter supporting JSON, JSONL, and CSV."""

    @staticmethod
    def export_json(data: Union[Dict[str, Any], List[Dict[str, Any]]], filepath: Union[str, Path], indent: int = 2) -> Path:
        """Export dictionary or list of dictionaries to a pretty JSON file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, default=str, ensure_ascii=False)
        logger.info(f"Exported JSON to {path}")
        return path

    @staticmethod
    def export_jsonl(records: List[Dict[str, Any]], filepath: Union[str, Path]) -> Path:
        """Export list of dictionary records to a JSON Lines file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, default=str, ensure_ascii=False) + "\n")
        logger.info(f"Exported JSONL ({len(records)} records) to {path}")
        return path

    @staticmethod
    def export_csv(records: List[Dict[str, Any]], filepath: Union[str, Path], fieldnames: Optional[List[str]] = None) -> Path:
        """Export list of dictionary records to a standard RFC 4180 CSV file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        if not records:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                if fieldnames:
                    writer.writerow(fieldnames)
            return path

        if not fieldnames:
            # Flatten keys from all records
            all_keys = {}
            for rec in records:
                for k in rec.keys():
                    all_keys[k] = True
            fieldnames = list(all_keys.keys())

        # Flatten nested list/dict structures for CSV columns
        flattened_records = []
        for rec in records:
            flat_rec = {}
            for k in fieldnames:
                val = rec.get(k)
                if isinstance(val, (dict, list)):
                    flat_rec[k] = json.dumps(val, default=str, ensure_ascii=False)
                else:
                    flat_rec[k] = val
            flattened_records.append(flat_rec)

        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(flattened_records)

        logger.info(f"Exported CSV ({len(records)} rows) to {path}")
        return path

    @classmethod
    def export_products(
        cls,
        products: List[Any],
        filepath: Union[str, Path],
        export_format: str = "json",
    ) -> Path:
        """
        Export normalized product records to target format ('json', 'jsonl', or 'csv').
        """
        dict_records: List[Dict[str, Any]] = []
        for p in products:
            if hasattr(p, "model_dump"):
                dict_records.append(p.model_dump())
            elif isinstance(p, dict):
                dict_records.append(p)

        fmt = export_format.lower().strip()
        path = Path(filepath)

        if fmt == "jsonl":
            if not path.suffix or path.suffix != ".jsonl":
                path = path.with_suffix(".jsonl")
            return cls.export_jsonl(dict_records, path)
        elif fmt == "csv":
            if not path.suffix or path.suffix != ".csv":
                path = path.with_suffix(".csv")
            return cls.export_csv(dict_records, path)
        else:
            if not path.suffix or path.suffix != ".json":
                path = path.with_suffix(".json")
            return cls.export_json(dict_records, path)

    @classmethod
    def export_reviews(
        cls,
        reviews: List[Any],
        filepath: Union[str, Path],
        export_format: str = "json",
    ) -> Path:
        """
        Export customer review records to target format ('json', 'jsonl', or 'csv').
        """
        dict_records: List[Dict[str, Any]] = []
        for r in reviews:
            if hasattr(r, "model_dump"):
                dict_records.append(r.model_dump())
            elif isinstance(r, dict):
                dict_records.append(r)

        fmt = export_format.lower().strip()
        path = Path(filepath)

        if fmt == "jsonl":
            if not path.suffix or path.suffix != ".jsonl":
                path = path.with_suffix(".jsonl")
            return cls.export_jsonl(dict_records, path)
        elif fmt == "csv":
            if not path.suffix or path.suffix != ".csv":
                path = path.with_suffix(".csv")
            return cls.export_csv(dict_records, path)
        else:
            if not path.suffix or path.suffix != ".json":
                path = path.with_suffix(".json")
            return cls.export_json(dict_records, path)
