from bs4 import BeautifulSoup


def extract_titles_from_grobid_xml(xml_text: str) -> list[str]:
    soup = BeautifulSoup(xml_text, "xml")
    titles = []

    for bibl in soup.find_all("biblStruct"):
        title = None

        analytic = bibl.find("analytic")
        if analytic and analytic.find("title"):
            title = analytic.find("title").get_text(strip=True)
        else:
            monogr = bibl.find("monogr")
            if monogr and monogr.find("title"):
                title = monogr.find("title").get_text(strip=True)

        if title:
            titles.append(title)

    return titles


if __name__ == "__main__":
    # quick sanity test
    sample_xml = """<biblStruct xml:id="b74">
        <analytic>
            <title level="a" type="main">
                UAV-based 3D modelling of disaster scenes for Urban Search and Rescue
            </title>
        </analytic>
    </biblStruct>"""

    print(extract_titles_from_grobid_xml(sample_xml))