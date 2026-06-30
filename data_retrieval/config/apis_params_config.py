museums_details = {
    "met": {
        "base_url": "https://collectionapi.metmuseum.org/public/collection/v1",
        "key": None,
        "exceptions": {
            "isPublicDomain": False,
            "objectName": ["fragment"],
            "title": ["fragment"],
        },
        "requirements": {},
        "results_per_page": None,
    },
    "rijks": {
        "base_url": "https://data.rijksmuseum.nl/search/collection?imageAvailable=true",
        "key": None,
        "exceptions": {},
        "requirements": {
            "subject_to[0].classified_as[0]._label": "public domain",
        },
    }
}