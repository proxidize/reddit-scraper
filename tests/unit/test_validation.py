import pytest
from reddit_scraper.validation import (
    ValidationError,
    validate_subreddit_name,
    validate_username,
    validate_post_id,
    validate_limit,
    validate_sort_method,
    validate_url,
    validate_delay,
    sanitize_filename
)


class TestSubredditValidation:
    
    def test_valid_subreddit_names(self):
        assert validate_subreddit_name("python") == "python"
        assert validate_subreddit_name("r/python") == "python"
        assert validate_subreddit_name("AskReddit") == "askreddit"
        assert validate_subreddit_name("test_sub") == "test_sub"
        assert validate_subreddit_name("123") == "123"
    
    def test_invalid_subreddit_names(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_subreddit_name("")
            
        with pytest.raises(ValidationError, match="Invalid subreddit name"):
            validate_subreddit_name("invalid!")
            
        with pytest.raises(ValidationError, match="Invalid subreddit name"):
            validate_subreddit_name("toolongsubredditname123456")
            
        with pytest.raises(ValidationError, match="Invalid subreddit name"):
            validate_subreddit_name("with-dash")
    
    def test_reserved_subreddit_names(self):
        with pytest.raises(ValidationError, match="reserved or problematic"):
            validate_subreddit_name("api")
            
        with pytest.raises(ValidationError, match="reserved or problematic"):
            validate_subreddit_name("www")


class TestUsernameValidation:
    
    def test_valid_usernames(self):
        assert validate_username("user123") == "user123"
        assert validate_username("u/user123") == "user123"
        assert validate_username("test_user") == "test_user"
    
    def test_invalid_usernames(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_username("")
            
        with pytest.raises(ValidationError, match="Invalid username"):
            validate_username("user!")


class TestPostIdValidation:
    
    def test_valid_post_ids(self):
        assert validate_post_id("abc123") == "abc123"
        assert validate_post_id("xyz789def") == "xyz789def"
    
    def test_invalid_post_ids(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_post_id("")
            
        with pytest.raises(ValidationError, match="Invalid post ID"):
            validate_post_id("invalid!")


class TestLimitValidation:
    
    def test_valid_limits(self):
        assert validate_limit(10) == 10
        assert validate_limit("25") == 25
        assert validate_limit(100) == 100
    
    def test_invalid_limits(self):
        with pytest.raises(ValidationError, match="must be a positive integer"):
            validate_limit(-1)
            
        with pytest.raises(ValidationError, match="must be a positive integer"):
            validate_limit(0)
            
        with pytest.raises(ValidationError, match="must be a positive integer"):
            validate_limit("invalid")
            
        with pytest.raises(ValidationError, match="Maximum limit is 1000"):
            validate_limit(1001)


class TestSortMethodValidation:
    
    def test_valid_sort_methods(self):
        assert validate_sort_method("hot") == "hot"
        assert validate_sort_method("new") == "new"
        assert validate_sort_method("top") == "top"
        assert validate_sort_method("rising") == "rising"
    
    def test_invalid_sort_methods(self):
        with pytest.raises(ValidationError, match="Invalid sort method"):
            validate_sort_method("invalid")
            
        with pytest.raises(ValidationError, match="Invalid sort method"):
            validate_sort_method("")


class TestUrlValidation:

    def test_valid_urls(self):
        valid_urls = [
            "https://reddit.com/r/python",
            "https://www.reddit.com/r/test/comments/abc123/",
            "http://old.reddit.com/r/askreddit"
        ]
        for url in valid_urls:
            assert validate_url(url) == url
    
    def test_invalid_urls(self):
        with pytest.raises(ValidationError, match="Invalid URL format"):
            validate_url("not-a-url")
            
        with pytest.raises(ValidationError, match="Invalid URL format"):
            validate_url("ftp://invalid.com")


class TestDelayValidation:
    
    def test_valid_delays(self):
        assert validate_delay(1.0) == 1.0
        assert validate_delay("2.5") == 2.5
        assert validate_delay(0) == 0
    
    def test_invalid_delays(self):
        with pytest.raises(ValidationError, match="must be a non-negative number"):
            validate_delay(-1)
            
        with pytest.raises(ValidationError, match="must be a non-negative number"):
            validate_delay("invalid")


class TestFilenameValidation:
    
    def test_sanitize_filename(self):
        assert sanitize_filename("normal_file.json") == "normal_file.json"
        assert sanitize_filename("file with spaces.json") == "file_with_spaces.json"
        assert sanitize_filename("file/with\\invalid:chars") == "file_with_invalid_chars"
        assert sanitize_filename("../../../etc/passwd") == ".._.._.._.._etc_passwd"
        assert sanitize_filename("") == "untitled"