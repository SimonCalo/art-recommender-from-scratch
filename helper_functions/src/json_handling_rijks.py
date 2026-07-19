"""Helper functions to unpack jsons coming from RIJKS museum API"""

import json
import requests
from typing import Any, Optional
from helper_functions.config.json_conversions_config import (
    en_id_rijks, nl_id_rijks, dimension_map_rijks, material_ids_rijks_config_path, description_id_rijks
)


def convert_input_number_to_date(input_number: int) -> str:
    """Convert integer number to date. Mainly used to handle
    dates before year 0.

    Args:
        input_number (int): Date in the form of a postive or negative integer.

    Returns:
        str: The number converted to a date. If the number is negative, the date
             will be the absolute number followed by BC.
    """

    if input_number < 0:
        input_number = f"{(input_number * -1)} BC"

    return str(input_number)


def load_cache(path: str = material_ids_rijks_config_path) -> dict[str, str]:
    """Load the Rijks ID cache from a JSON file.
    
    If the file doesn't exist, initializes an empty cache.
    
    Args:
        path: Path to the cache file. Defaults to material_ids_rijks_config_path.

    Returns:
        dict[str, str]: Dictionary containing the rijks id conversions.    
    """
    try:
        with open(path) as f:
            rijks_id_cache = json.load(f)
    except FileNotFoundError:
        rijks_id_cache = {}

    return rijks_id_cache


def save_cache(rijks_id_cache: dict[str, str], path: str = material_ids_rijks_config_path) -> None:
    """Save the Rijks ID cache to a JSON file.
    
    Args:
        rijks_id_cache (dict[str, str]): The dictionary containing information to convert ids to materials.
        path: Path to the cache file. Defaults to material_ids_rijks_config_path.
    """
    with open(path, "w") as f:
        json.dump(rijks_id_cache, f, indent=2)


def has_language(obj: dict[str, Any], lang_code: str) -> bool:
    """Check if an object has a language matching the given language code.
    
    Args:
        obj (dict[str, Any]): Dictionary that may contain language information.
        lang_code (str): Language code to check for (e.g. "300388277" for English).
    
    Returns:
        bool: True if the object has a language matching the code, False otherwise.
    """
    return any(
        lang.get("id", "").endswith(lang_code)
        for lang in obj.get("language", [])
    )


def resolve_rijks_id_to_label(rijks_id: str, rijks_id_cache: dict[str, str], language: str = en_id_rijks) -> str:
    """Resolve a Rijks ID to a human-readable label.
    
    First checks the cache, then attempts to fetch from the Rijks API.
    Falls back to the ID fragment if resolution fails.
    
    Args:
        rijks_id (str): The Rijks ID URL to resolve.
        rijks_id_cache (dict[str, str]): The dictionary containing information to convert ids to materials.
        language (str): Language code for preferred label. Defaults to en_id_rijks, which is the English language.
    
    Returns:
        str: The resolved label indicating the material, or 'unknown' as a fallback.
    """
    if rijks_id in rijks_id_cache:
        return rijks_id_cache[rijks_id]

    try:
        response = requests.get(rijks_id, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Look for language-specific label first, then fallback to any available label
        fallback_label = None
        for ident in data.get("identified_by", []):
            if ident.get("type") != "Name":
                continue
            
            label = ident.get("content", "").strip()
            if not label:
                continue
            
            # Check if this label matches the preferred language
            if has_language(ident, language):
                rijks_id_cache[rijks_id] = label
                return label
            
            # Store first available label as fallback
            if fallback_label is None:
                fallback_label = label
        
        # Use fallback if language-specific label not found
        if fallback_label:
            rijks_id_cache[rijks_id] = fallback_label
            return fallback_label

    except Exception as e:
        print(f"[WARN] Failed to resolve {rijks_id}: {e}")
    
    return "unknown"


def has_classification(obj: dict[str, Any], aat_code: str) -> bool:
    """Check if an object has a classification matching the given AAT code.
    
    Args:
        obj (dict): Dictionary object that may contain classification information.
        aat_code (str): AAT (Art & Architecture Thesaurus) code to check for.
    
    Returns:
        bool: True if the object has a classification matching the code, False otherwise.
    """
    return any(
        c.get("id", "").endswith(aat_code)
        for c in obj.get("classified_as", [])
        if isinstance(c, dict)
    )


def get_linguistic_objects(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract all linguistic objects from metadata.
    
    Combines objects from "referred_to_by" and "subject_of" fields.
    
    Args:
        metadata (dict[str, Any]): Dictionary containing artwork metadata.
    
    Returns:
        list[dict[str, Any]]: List of linguistic object dictionaries.
    """
    return (
        metadata.get("referred_to_by", [])
        + metadata.get("subject_of", [])
    )


def extract_title(metadata: dict[str, Any]) -> tuple[str, str]:
    """Extract English and original language titles from metadata.
    
    Args:
        metadata (dict[str, Any]): Dictionary containing artwork metadata.
    
    Returns:
        tuple[str, str]: Tuple of (English title, original language title).
                         Empty strings if not found.
    """
    titles = metadata.get("identified_by", [])

    title_en = ""
    title_orig = ""

    for t in titles:
        if t.get("type") != "Name":
            continue
        if has_language(t, en_id_rijks):
            title_en = t.get("content", "")
        elif has_language(t, nl_id_rijks):
            title_orig = t.get("content", "")

    return title_en, title_orig


def extract_artist(metadata: dict[str, Any]) -> str:
    """Extract the main artist name from metadata.
    
    Args:
        metadata (dict[str, Any]): Dictionary containing artwork metadata.
    
    Returns:
        str: The artist name, or "Anonymous" if not found.
    """
    produced_by = metadata.get("produced_by", {})
    parts = produced_by.get("part", [])
    artist = ""

    for part in parts:
        for ref in part.get("referred_to_by", []):
            if ref.get("type") == "LinguisticObject":
                artist = ref.get("content", "")

    if artist.lower() in ["", "anoniem", "anonymous"]:
        artist = "Anonymous"

    return artist


def parse_year_from_iso(date_str: str | None) -> int | None:
    """
    Extract signed year from ISO 8601 date string.

    Args:
        date_str (str | None): The date string to parse.

    Returns:
        int | None: The signed year, or None if parsing fails.
    """
    if not date_str or not isinstance(date_str, str):
        return None

    try:
        if date_str.startswith("-"):
            return -int(date_str[1:5])
        return int(date_str.split("-")[0])
    except ValueError:
        return None


def extract_dates(metadata: dict[str, Any]) -> tuple[Optional[int], Optional[str], Optional[int], Optional[str]]:
    """Extract start and end dates from metadata.
    
    Parses ISO 8601 date strings and converts them to years and formatted date strings.
    If only one date is available, it is used for both start and end.
    
    Args:
        metadata (dict[str, Any]): Dictionary containing artwork metadata.
    
    Returns:
        tuple[
            Optional[int],
            Optional[str],
            Optional[int],
            Optional[str],
        ]: Tuple of (start_year, start_date_string, end_year, end_date_string).
           All values are None if dates cannot be extracted.
    """
    timespan = (
        metadata
        .get("produced_by", {})
        .get("timespan", {})
    )

    start_raw = timespan.get("begin_of_the_begin")
    end_raw = timespan.get("end_of_the_end")

    start = parse_year_from_iso(start_raw)
    end = parse_year_from_iso(end_raw)

    # If only one side exists, mirror it
    if start is None and end is not None:
        start = end
    if end is None and start is not None:
        end = start

    if start is None and end is None:
        return None, None, None, None

    return (
        start,
        convert_input_number_to_date(start) if start is not None else None,
        end,
        convert_input_number_to_date(end) if end is not None else None,
    )


def extract_dimensions(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract dimension information from metadata.
    
    Args:
        metadata (dict[str, Any]): Dictionary containing artwork metadata.
    
    Returns:
        list[dict[str, Any]]: List of dimension dictionaries, each with "type", "value", and "unit" keys.
    """
    dims = []

    for d in metadata.get("dimension", []):
        dim_type = None
        for c in d.get("classified_as", []):
            for key, name in dimension_map_rijks.items():
                if c["id"].endswith(key):
                    dim_type = name

        if dim_type:
            dims.append(
                {
                    "type": dim_type,
                    "value": float(d["value"]),
                    "unit": "cm",
                }
            )

    return dims


def extract_descriptions(metadata: dict[str, Any]) -> tuple[str, str]:
    """Extract long descriptions in English and Dutch from metadata.
    
    Args:
        metadata (dict[str, Any]): Dictionary containing artwork metadata.
    
    Returns:
        tuple[str, str]: Tuple of (English description, Dutch description). Empty strings if not found.
    """
    long_en = ""
    long_nl = ""

    for obj in get_linguistic_objects(metadata):
        if obj.get("type") != "LinguisticObject":
            continue

        if has_classification(obj, description_id_rijks):
            if has_language(obj, en_id_rijks):
                long_en = obj.get("content", "")
            elif has_language(obj, nl_id_rijks):
                long_nl = obj.get("content", "")

    return long_en, long_nl


def extract_material_label(material: dict[str, Any], rijks_id_cache: dict[str, str], language: str = en_id_rijks) -> str:
    """Resolve a material to a human-readable label.
    
    First tries to find embedded labels in the material object, then falls back
    to resolving via the Rijks ID using the cache or API.
    
    Args:
        material (dict[str, Any]): Dictionary containing material information.
        rijks_id_cache (dict[str, str]): The dictionary containing information to convert ids to materials.
        language (str): Language code for preferred label. Defaults to en_id_rijks.
    
    Returns:
        str: The material label, or empty string if not found.
    """
    # First try embedded labels
    for ident in material.get("identified_by", []):
        if ident.get("type") == "Name":
            if has_language(ident, language) or not ident.get("language"):
                label = ident.get("content", "").strip()
                if label:
                    return label

    # Fallback: resolve via Rijks ID
    material_id = material.get("id")
    if material_id:
        return resolve_rijks_id_to_label(material_id, rijks_id_cache, language)

    return ""


def extract_materials(metadata: dict[str, Any], rijks_id_cache: dict[str, str], language: str = en_id_rijks) -> list[str]:
    """Extract material labels from metadata.
    
    Args:
        metadata (dict[str, Any]): Dictionary containing artwork metadata.
        rijks_id_cache (dict[str, str]): The dictionary containing information to convert ids to materials.
        language (str): Language code for preferred labels. Defaults to en_id_rijks.
    
    Returns:
        list[str]: List of unique material labels.
    """
    materials = []

    for mat in metadata.get("made_of", []):
        if mat.get("type") != "Material":
            continue

        label = extract_material_label(mat, rijks_id_cache, language)
        if label:
            materials.append(label)

    return list(dict.fromkeys(materials))