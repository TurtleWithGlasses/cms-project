"""
Tests for slugify utility function

Tests URL slug generation from strings with various edge cases.
"""

import pytest

from app.utils.slugify import slugify


class TestSlugifyBasic:
    """Test basic slugify functionality"""

    def test_slugify_simple_string(self):
        """Test slugifying a simple string"""
        assert slugify("Hello World") == "hello-world"

    def test_slugify_with_numbers(self):
        """Test slugifying string with numbers"""
        assert slugify("Product 123") == "product-123"

    def test_slugify_lowercase_conversion(self):
        """Test that slugify converts to lowercase"""
        assert slugify("UPPERCASE TEXT") == "uppercase-text"
        assert slugify("MiXeD CaSe") == "mixed-case"

    def test_slugify_removes_special_characters(self):
        """Test that special characters are replaced with hyphens"""
        assert slugify("Hello@World!") == "hello-world"
        assert slugify("Test & Demo") == "test-demo"
        assert slugify("Price: $99.99") == "price-99-99"

    def test_slugify_multiple_spaces(self):
        """Test that multiple spaces are collapsed to single hyphen"""
        assert slugify("Hello    World") == "hello-world"
        assert slugify("Too   Many   Spaces") == "too-many-spaces"


class TestSlugifyUnicode:
    """Test slugify with unicode and international characters"""

    def test_slugify_accented_characters(self):
        """Test slugifying strings with accented characters"""
        assert slugify("Café") == "cafe"
        assert slugify("Naïve") == "naive"
        assert slugify("Résumé") == "resume"

    def test_slugify_german_umlauts(self):
        """Test slugifying German umlauts"""
        assert slugify("Über") == "uber"
        assert slugify("Größe") == "grosse"

    def test_slugify_spanish_characters(self):
        """Test slugifying Spanish characters"""
        assert slugify("Año Nuevo") == "ano-nuevo"
        assert slugify("Niño") == "nino"

    def test_slugify_cyrillic(self):
        """Test slugifying Cyrillic characters"""
        result = slugify("Привет")
        assert result  # Should produce some ASCII output
        assert "-" not in result or len(result) > 1  # Not just hyphens


class TestSlugifyEdgeCases:
    """Test edge cases and error handling"""

    def test_slugify_empty_string_raises_error(self):
        """Test that empty string raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            slugify("")

        assert "non-empty" in str(exc_info.value).lower()

    def test_slugify_none_raises_error(self):
        """Test that None raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            slugify(None)

        assert "non-empty" in str(exc_info.value).lower()

    def test_slugify_only_special_characters(self):
        """Test slugifying string with only special characters"""
        result = slugify("@#$%^&*()")
        assert result == "n-a"  # Fallback for empty result

    def test_slugify_leading_trailing_hyphens(self):
        """Test that leading/trailing hyphens are stripped"""
        assert slugify("-Hello World-") == "hello-world"
        assert slugify("---Test---") == "test"

    def test_slugify_consecutive_hyphens(self):
        """Test that consecutive special chars create single hyphen"""
        assert slugify("Hello!!!World") == "hello-world"
        assert slugify("Test---Demo") == "test-demo"

    def test_slugify_numbers_only(self):
        """Test slugifying numbers only"""
        assert slugify("12345") == "12345"
        assert slugify("2024") == "2024"

    def test_slugify_single_word(self):
        """Test slugifying single word"""
        assert slugify("Hello") == "hello"
        assert slugify("Test123") == "test123"


class TestSlugifyRealWorld:
    """Test slugify with real-world use cases"""

    def test_slugify_article_title(self):
        """Test slugifying article titles"""
        assert slugify("How to Build a REST API") == "how-to-build-a-rest-api"
        assert slugify("10 Tips for Success!") == "10-tips-for-success"

    def test_slugify_product_name(self):
        """Test slugifying product names"""
        assert slugify("iPhone 15 Pro Max") == "iphone-15-pro-max"
        assert slugify("Samsung Galaxy S24+") == "samsung-galaxy-s24"

    def test_slugify_category_name(self):
        """Test slugifying category names"""
        assert slugify("Home & Garden") == "home-garden"
        assert slugify("Books, Music & Movies") == "books-music-movies"

    def test_slugify_user_generated_content(self):
        """Test slugifying user-generated content"""
        assert slugify("My Awesome Blog Post!!!") == "my-awesome-blog-post"
        assert slugify("Review: Best Coffee Maker (2024)") == "review-best-coffee-maker-2024"

    def test_slugify_long_string(self):
        """Test slugifying a long string"""
        long_title = "This is a Very Long Title That Contains Many Words and Should Still Work Correctly"
        result = slugify(long_title)
        assert result.startswith("this-is-a-very-long")
        assert "correctly" in result
        assert result.count("-") > 5  # Multiple hyphens for spaces


class TestSlugifyConsistency:
    """Test consistency and idempotency"""

    def test_slugify_is_consistent(self):
        """Test that slugify produces consistent results"""
        text = "Test Article Title"
        result1 = slugify(text)
        result2 = slugify(text)
        assert result1 == result2

    def test_slugify_different_inputs_different_outputs(self):
        """Test that different inputs produce different slugs"""
        slug1 = slugify("Article One")
        slug2 = slugify("Article Two")
        assert slug1 != slug2
        assert slug1 == "article-one"
        assert slug2 == "article-two"

    def test_slugify_similar_strings(self):
        """Test slugifying similar but different strings"""
        slug1 = slugify("Test-Post")
        slug2 = slugify("Test Post")
        assert slug1 == slug2  # Both should become "test-post"
