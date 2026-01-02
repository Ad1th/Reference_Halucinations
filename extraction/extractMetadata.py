"""
Extract full metadata from GROBID XML references.
Returns structured data for each reference including:
- title, authors, year, venue, pages, volume, doi
"""
from bs4 import BeautifulSoup
from typing import List, Dict, Optional


def extract_references_metadata(xml_text: str) -> List[Dict]:
    """
    Extract full metadata from all references in GROBID XML.
    
    Returns list of dicts with keys:
        - title: str
        - authors: List[str]
        - year: str | None
        - venue: str | None
        - pages: str | None
        - volume: str | None
        - doi: str | None
    """
    soup = BeautifulSoup(xml_text, "xml")
    references = []

    for bibl in soup.find_all("biblStruct"):
        ref = extract_single_reference(bibl)
        if ref.get("title"):  # Only include if we have a title
            references.append(ref)

    return references


def extract_single_reference(bibl) -> Dict:
    """Extract metadata from a single biblStruct element."""
    ref = {
        "title": None,
        "authors": [],
        "year": None,
        "venue": None,
        "pages": None,
        "volume": None,
        "doi": None
    }
    
    # Title - check analytic first (article title), then monogr (book/journal title)
    analytic = bibl.find("analytic")
    monogr = bibl.find("monogr")
    
    if analytic and analytic.find("title"):
        ref["title"] = analytic.find("title").get_text(strip=True)
    elif monogr and monogr.find("title"):
        ref["title"] = monogr.find("title").get_text(strip=True)
    
    # Authors - from analytic or monogr
    authors_container = analytic if analytic else monogr
    if authors_container:
        ref["authors"] = extract_authors(authors_container)
    
    # Year
    date = bibl.find("date", {"type": "published"})
    if date:
        when = date.get("when", "")
        ref["year"] = when[:4] if when else date.get_text(strip=True)[:4] if date.get_text(strip=True) else None
    
    # Venue (journal/conference name from monogr)
    if monogr:
        venue_title = monogr.find("title")
        if venue_title:
            ref["venue"] = venue_title.get_text(strip=True)
    
    # Pages
    pages = bibl.find("biblScope", {"unit": "page"})
    if pages:
        from_page = pages.get("from")
        to_page = pages.get("to")
        if from_page and to_page:
            ref["pages"] = f"{from_page}-{to_page}"
        elif from_page:
            ref["pages"] = from_page
        elif pages.get_text(strip=True):
            ref["pages"] = pages.get_text(strip=True)
    
    # Volume
    volume = bibl.find("biblScope", {"unit": "volume"})
    if volume:
        ref["volume"] = volume.get_text(strip=True) or volume.get("from")
    
    # DOI
    doi = bibl.find("idno", {"type": "DOI"})
    if doi:
        ref["doi"] = doi.get_text(strip=True)
    
    return ref


def extract_authors(container) -> List[str]:
    """Extract author names from a container element."""
    authors = []
    for author in container.find_all("author"):
        persName = author.find("persName")
        if persName:
            forename = persName.find("forename")
            surname = persName.find("surname")
            
            first = forename.get_text(strip=True) if forename else ""
            last = surname.get_text(strip=True) if surname else ""
            
            name = f"{first} {last}".strip()
            if name:
                authors.append(name)
    return authors


if __name__ == "__main__":
    # Quick test
    sample_xml = """
    <biblStruct xml:id="b0">
        <analytic>
            <title level="a" type="main">Deep Learning for Entity Matching</title>
            <author>
                <persName><forename type="first">John</forename><surname>Doe</surname></persName>
            </author>
            <author>
                <persName><forename type="first">Jane</forename><surname>Smith</surname></persName>
            </author>
            <idno type="DOI">10.1145/1234567.1234568</idno>
        </analytic>
        <monogr>
            <title level="m">Proceedings of SIGMOD</title>
            <imprint>
                <date type="published" when="2023"/>
                <biblScope unit="volume">15</biblScope>
                <biblScope unit="page" from="100" to="115"/>
            </imprint>
        </monogr>
    </biblStruct>
    """
    
    refs = extract_references_metadata(sample_xml)
    for ref in refs:
        print(ref)
