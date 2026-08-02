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


def test_rank_includes_multiple_sources() -> None:
    books = [
        Book(
            id="gutenberg",
            provider="gutenberg",
            provider_id="1",
            title="Python Machine Learning",
        ),
        Book(
            id="arxiv",
            provider="arxiv",
            provider_id="2",
            title="Machine Learning Research",
        ),
    ]
    ranked = merge_and_rank(books, SearchFilters(title="machine learning", limit=2))
    assert {book.provider for book in ranked} == {"gutenberg", "arxiv"}


def test_search_filters_normalize_terminal_input() -> None:
    filters = SearchFilters(title="  metaphysics  ", author=" aristotle ")
    assert filters.title == "metaphysics"
    assert filters.author == "aristotle"
