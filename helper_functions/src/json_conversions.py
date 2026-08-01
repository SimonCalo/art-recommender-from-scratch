"""Helper functions to convert museum-specific jsons to standard format jsons."""
from datetime import datetime
import os
import json
from typing import Any
from helper_functions.config.json_conversions_config import (
    final_metadata_template, valid_dimension_types_artic, en_id_rijks,
    artic_field_mappings, artic_nested_mappings,
    met_field_mappings, met_production_place_fields,
)
from helper_functions.src.json_handling_rijks import (
    load_cache,
    save_cache,
    extract_materials,
    extract_artist,
    extract_title,
    extract_dimensions,
    extract_descriptions,
    extract_dates,
    convert_input_number_to_date,  # NOTE: this one is not rijks specific
)


def convert_rijks_json_to_standard_json(original_metadata: dict[str, Any]) -> dict[str, Any]:
    """Convert JSON from the Rijksmuseum API into the standard format.
    
    More information regarding the standard format can be found in our documentation.
    
    Args:
        original_metadata: The metadata dictionary pulled from the Rijksmuseum API.
    
    Returns:
        The final metadata dictionary with filled in information in standard format.
    """
    final = final_metadata_template.copy()

    final["original_id"] = original_metadata["id"].split("/")[-1]

    # this cache is used to convert material ids to descriptions
    rijks_id_cache = load_cache()

    (
        final["title_english"],
        final["title_original_language"],
    ) = extract_title(original_metadata)

    final["main_artist"] = extract_artist(original_metadata)

    (
        final["year_start_number"],
        final["year_start"],
        final["year_end_number"],
        final["year_end"],
    ) = extract_dates(original_metadata)

    final["dimensions"] = extract_dimensions(original_metadata)

    (
        final["long_description_english"],
        final["long_description_original_language"],
    ) = extract_descriptions(original_metadata)

    final["museum_api_from_which_it_was_retrieved"] = "rijks"
    final["location"] = "Rijks Museum Amsterdam"
    final["artwork_materials"] = extract_materials(
        original_metadata, rijks_id_cache, language=en_id_rijks
    )

    save_cache(rijks_id_cache)

    return final


def convert_artic_json_to_standard_json(original_metadata: dict[str, Any]) -> dict[str, Any]:
    """Function to convert jsons from the ARTIC API into the standard format.
    More information regarding the standard format can be found in our documentation.

    Args:
        original_metadata: The metadata dictionary pulled from the ARTIC API.

    Returns:
        The final metadata with filled in information.
    """
    final_metadata = final_metadata_template.copy()

    # Direct field mappings
    for source_key, target_key in artic_field_mappings.items():
        if source_key in original_metadata:
            final_metadata[target_key] = original_metadata[source_key]

    # Artist details
    final_metadata["artists_details"] = [{
        "artist_summary": original_metadata.get("artist_display", ""),
        "place_of_origin": original_metadata.get("place_of_origin", ""),
    }]

    final_metadata["museum_api_from_which_it_was_retrieved"] = "artic"

    if original_metadata.get("is_on_view"):
        final_metadata["location"] = "Art Institute of Chicago"

    year_start = int(original_metadata["date_start"])
    final_metadata["year_start_number"] = year_start
    final_metadata["year_start"] = convert_input_number_to_date(year_start)

    year_end = int(original_metadata["date_end"])
    final_metadata["year_end_number"] = year_end
    final_metadata["year_end"] = convert_input_number_to_date(year_end)

    final_metadata["dating_of_first_display"] = str(original_metadata["date_display"])

    dimensions = original_metadata["dimensions"]
    final_dim = []
    for original_entry in dimensions:
        entry = original_entry.removesuffix('_cm')
        if entry not in valid_dimension_types_artic:
            continue
        
        property_value = dimensions[original_entry]
        if property_value is None:
            continue

        try:
            property_value = float(property_value)
        except ValueError:
            property_value = -1.0

        final_dim.append({
            "type": entry,
            "value": property_value,
            "unit": "cm"
        })
    final_metadata["dimensions"] = final_dim

    artwork_types = [
        original_metadata["artwork_type_title"].lower().strip(),
        *original_metadata["classification_titles"],
        original_metadata["medium_display"],
    ]
    final_metadata["artwork_types"] = list(set(artwork_types))

    artwork_categories = [
        *original_metadata["category_titles"],
        *original_metadata["term_titles"],
    ]
    final_metadata["artwork_categories"] = list(set(artwork_categories))

    for source, target_key in artic_nested_mappings.items():
        if isinstance(source, tuple):
            if source[0] in original_metadata and source[1] in original_metadata[source[0]]:
                final_metadata[target_key] = original_metadata[source[0]][source[1]]
        elif source in original_metadata:
            final_metadata[target_key] = original_metadata[source]

    if "publication_history" in original_metadata:
        final_metadata["documents_and_publications"] = (
            original_metadata["publication_history"].split("\n\n")
        )

    return final_metadata


def convert_met_json_to_standard_json(
    original_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Function to convert jsons from the Met museum API into the standard format.
    More information regarding the standard format can be found in our documentation.

    Args:
        original_metadata: The metadata dictionary pulled from the Met API.

    Returns:
        The final metadata with filled in information.
    """
    final_metadata = final_metadata_template.copy()

    # Direct field mappings
    for source_key, target_key in met_field_mappings.items():
        if source_key in original_metadata:
            final_metadata[target_key] = original_metadata[source_key]

    final_metadata["artists"] = [original_metadata["artistDisplayName"]]
    final_metadata["main_artist"] = original_metadata["artistDisplayName"]
    
    final_metadata["artists_details"] = {
        key: original_metadata[key]
        for key in original_metadata.keys()
        if 'artist' in key.lower()
    }
    
    final_metadata["museum_api_from_which_it_was_retrieved"] = "met"

    year_start = int(original_metadata["objectBeginDate"])
    final_metadata["year_start_number"] = year_start
    final_metadata["year_start"] = convert_input_number_to_date(year_start)

    year_end = int(original_metadata["objectEndDate"])
    final_metadata["year_end_number"] = year_end
    final_metadata["year_end"] = convert_input_number_to_date(year_end)

    final_metadata["dating_of_first_display"] = str(original_metadata["accessionYear"])

    final_metadata["production_places"] = [
        original_metadata.get(field, '')
        for field in met_production_place_fields
    ]
    
    final_metadata["main_production_place"] = (
        f"{original_metadata.get('city', '')}, "
        f"{original_metadata.get('country', '')}"
    )

    dimensions = ''
    if isinstance(original_metadata.get("measurements"), list) and original_metadata["measurements"]:
        dimensions = original_metadata["measurements"][0].get("elementMeasurements", {})
    
    final_dim = []
    if isinstance(dimensions, dict):
        for property_type, property_value in dimensions.items():
            if property_value is None:
                continue

            try:
                property_value = float(property_value)
            except ValueError:
                property_value = -1.0

            final_dim.append({
                "type": property_type,
                "value": property_value,
                "unit": "cm"
            })
    final_metadata["dimensions"] = final_dim

    final_metadata["artwork_techniques"] = [original_metadata["medium"]]
    final_metadata["artwork_types"] = original_metadata["objectName"]

    final_metadata["location"] = "Metropolitan Museum of New York"
    final_metadata["location_within_museum"] = (
        f'Gallery {original_metadata.get("GalleryNumber", "")}'
    )

    return final_metadata


def convert_museum_jsons_to_standard_jsons(
    input_folder_path: str, output_folder_path: str, museum: str
) -> None:
    """Function to convert all jsons in a folder to standard format.

    Args:
        input_folder_path: The folder containing the jsons to be converted.
        output_folder_path: The folder where the converted jsons should be saved.
        museum: The museum from which the input jsons were taken.
    """
    
    museum_to_conversion_function = {
        "rijks": convert_rijks_json_to_standard_json,
        "artic": convert_artic_json_to_standard_json,
        "met": convert_met_json_to_standard_json,
    }

    today_date = datetime.today()

    # Format the date as a string ('YYYY-MM-DD')
    date_string = today_date.strftime('%Y-%m-%d')
        
    files = [
        input_folder_path + "/" +
        file for file in os.listdir(input_folder_path) if file.endswith(".json")
        ]

    for filename in files:
        with open(filename, 'r') as file:
            original_metadata = json.load(file)

        final_metadata = museum_to_conversion_function[museum](
            original_metadata=original_metadata,
            )

        final_metadata["date_processed"] = date_string

        final_name_without_extension = os.path.splitext(os.path.basename(filename))[0]

        output_file_path = f"{output_folder_path}/{final_name_without_extension}.json"

        if not os.path.exists(output_folder_path):
            os.makedirs(output_folder_path)

        with open(output_file_path, 'w') as json_file:
            json.dump(final_metadata, json_file)
