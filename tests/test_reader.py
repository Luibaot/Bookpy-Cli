import zipfile

from bookpy_cli.reader import read_book


def test_reads_plain_text(tmp_path) -> None:
    path = tmp_path / "book.txt"
    path.write_text("A small\n\nbook.")
    assert read_book(path) == "A small\n\nbook."


def test_reads_epub_spine_in_order(tmp_path) -> None:
    path = tmp_path / "book.epub"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "META-INF/container.xml",
            '<container><rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles></container>',
        )
        archive.writestr(
            "OEBPS/content.opf",
            '<package><manifest><item id="one" href="one.xhtml"/><item id="two" href="two.xhtml"/></manifest><spine><itemref idref="one"/><itemref idref="two"/></spine></package>',
        )
        archive.writestr("OEBPS/one.xhtml", "<h1>First</h1><p>One.</p>")
        archive.writestr("OEBPS/two.xhtml", "<h1>Second</h1><p>Two.</p>")
    assert read_book(path) == "First\nOne.\n\nSecond\nTwo."
