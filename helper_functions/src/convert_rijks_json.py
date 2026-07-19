"""Example of logic to convert JSON structure into standard format."""

from copy import deepcopy
from datetime import datetime

from helper_functions.config.metadata_template import metadata_template


def map_rijksmuseum_metadata(api_json):
    """
    Maps a Rijksmuseum object JSON (returned by /collection/{objectNumber})
    to the unified metadata template.

    Parameters
    ----------
    api_json : dict
        Full JSON response from the Rijksmuseum API.

    Returns
    -------
    dict
        Metadata in the unified format.
    """

    art = api_json.get("artObject", {})

    metadata = metadata_template.copy()
    metadata["museum_api_from_which_it_was_retrieved"] = "Rijksmuseum"
    metadata["location"] = "Rijksmuseum, Amsterdam"

    metadata["original_id"] = art.get("objectNumber", "")

    metadata["title_original_language"] = art.get("title", "")

    metadata["title_english"] = (
        art.get("label", {}).get("title")
        or art.get("title", "")
    )

    principal_makers = art.get("principalMakers", [])

    metadata["artists"] = [
        maker.get("name")
        for maker in principal_makers
        if maker.get("name")
    ]

    metadata["main_artist"] = art.get("principalOrFirstMaker", "")

    metadata["artists_details"] = deepcopy(principal_makers)

    dating = art.get("dating", {})

    year_early = dating.get("yearEarly")
    year_late = dating.get("yearLate")

    if isinstance(year_early, str):
        if "bc" in year_early.lower():
            year_early_normalised = -int(year_early.split(" ")[0])
            metadata["year_start_number"] = year_early_normalised
            metadata["year_start"] = year_early

    if isinstance(year_late, str):
        if "bc" in year_late.lower():
            year_late_normalised = -int(year_late.split(" ")[0])
            metadata["year_start_number"] = year_late_normalised
            metadata["year_start"] = year_late

    if isinstance(year_early, int):
        metadata["year_start_number"] = year_early
        metadata["year_start"] = str(year_early)

    if isinstance(year_late, int):
        metadata["year_end_number"] = year_late
        metadata["year_end"] = str(year_late)

    metadata["dating_of_first_display"] = dating.get("presentingDate", "")

    production_places = art.get("productionPlaces", [])

    metadata["production_places"] = production_places

    if production_places:
        metadata["main_production_place"] = production_places[0]

    metadata["dimensions"] = deepcopy(art.get("dimensions", []))

    metadata["artwork_style"] = art.get("styles", [])
    metadata["artwork_materials"] = art.get("materials", [])
    metadata["artwork_techniques"] = art.get("techniques", [])
    metadata["artwork_types"] = art.get("objectTypes", [])
    metadata["artwork_categories"] = art.get("objectCollection", [])

    classification = art.get("classification", {})

    metadata["artwork_subjects"] = classification.get(
        "iconClassDescriptions", []
    )

    themes = []

    for key in [
        "people",
        "events",
        "places",
        "motifs",
        "periods",
        "eventsPersons",
    ]:
        value = classification.get(key, [])
        if isinstance(value, list):
            themes.extend(value)

    metadata["artwork_themes"] = list(dict.fromkeys(themes))

    metadata["subject_description_original_language"] = art.get(
        "description", ""
    )

    metadata["short_description_original_language"] = (
        art.get("label", {}).get("description", "")
    )

    metadata["long_description_original_language"] = (
        art.get("description", "")
    )

    metadata["other_descriptions_original_language"] = art.get(
        "documentation", []
    )

    # NOTE:
    # These fields only contain English if the object was requested
    # using ?culture=en.
    metadata["subject_description_english"] = art.get("description", "")

    metadata["short_description_english"] = (
        art.get("label", {}).get("description", "")
    )

    metadata["long_description_english"] = (
        art.get("plaqueDescriptionEnglish")
        or art.get("description", "")
    )

    metadata["other_descriptions_english"] = art.get(
        "documentation", []
    )

    metadata["colours"] = [
        c["hex"]
        for c in art.get("colors", [])
        if "hex" in c
    ]

    metadata["normalised_colours"] = [
        c["hex"]
        for c in art.get("normalizedColors", [])
        if "hex" in c
    ]

    metadata["location_within_museum"] = art.get("location", "")

    metadata["department_within_museum"] = (
        art.get("acquisition", {}).get("creditLine", "")
    )

    metadata["documents_and_publications"] = art.get(
        "documentation", []
    )

    metadata["date_processed"] = datetime.utcnow().isoformat()

    return metadata