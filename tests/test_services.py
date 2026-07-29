from bookpy_cli.models import AccessType, Book, BookFormat, SearchFilters
from bookpy_cli.services import merge_and_rank


def test_merge_matches_normalized_title_and_author() -> None:
    left = Book(
        id="one",
        provider="first",
        provider_id="1",
        title="Pride & Prejudice",
        authors=["Jane Austen"],
        formats=[BookFormat.EPUB],
        access=AccessType.FREE,
    )
    right = Book(
        id="two",
        provider="second",
        provider_id="2",
        title="Pride and Prejudice",
        authors=["Jane Austen"],
        formats=[BookFormat.PDF],
        access=AccessType.METADATA,
    )
    merged = merge_and_rank([left, right], SearchFilters(title="Pride and Prejudice"))
    assert len(merged) == 1
    assert set(merged[0].formats) == {BookFormat.EPUB, BookFormat.PDF}
