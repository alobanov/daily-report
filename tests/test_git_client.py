import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from git_daily_report import GitClient, GitConfig

@pytest.fixture
def git_config():
    return GitConfig(
        repo_path="/test/repo",
        author_email="test@example.com",
        target_date=datetime(2024, 3, 14)
    )

@pytest.fixture
def git_client(git_config):
    return GitClient(git_config)

def test_init_with_repo_path(git_config):
    client = GitClient(git_config)
    assert client._base_cmd == ["git", "-C", "/test/repo"]

def test_init_without_repo_path():
    config = GitConfig(
        repo_path=None,
        author_email="test@example.com",
        target_date=datetime(2024, 3, 14)
    )
    client = GitClient(config)
    assert client._base_cmd == ["git"]

@patch('subprocess.check_output')
def test_get_username_success(mock_check_output, git_client):
    mock_check_output.return_value = b"Test User"
    assert git_client.get_username() == "Test User"
    mock_check_output.assert_called_once_with(["git", "-C", "/test/repo", "config", "user.name"])

@patch('subprocess.check_output')
def test_get_username_failure(mock_check_output, git_client):
    mock_check_output.side_effect = Exception("Git command failed")
    with pytest.raises(Exception) as exc_info:
        git_client.get_username()
    assert str(exc_info.value) == "Git command failed"

@patch('subprocess.check_output')
def test_get_commit_details_success(mock_check_output, git_client):
    mock_check_output.return_value = b"* abc123 2024-03-14 Test commit"
    result = git_client.get_commit_details("abc123")
    assert result == "* abc123 2024-03-14 Test commit"
    mock_check_output.assert_called_once()

@patch('subprocess.check_output')
def test_get_commit_details_failure(mock_check_output, git_client):
    mock_check_output.side_effect = Exception("Git command failed")
    with pytest.raises(Exception) as exc_info:
        git_client.get_commit_details("abc123")
    assert str(exc_info.value) == "Git command failed"

@patch('subprocess.check_output')
def test_get_commits_by_author_success(mock_check_output, git_client):
    mock_check_output.return_value = b"abc123\ndef456"
    result = git_client.get_commits_by_author("2024-03-14", "2024-03-15", "test@example.com")
    assert result == ["abc123", "def456"]
    mock_check_output.assert_called_once()

@patch('subprocess.check_output')
def test_get_commits_by_author_failure(mock_check_output, git_client):
    mock_check_output.side_effect = Exception("Git command failed")
    with pytest.raises(Exception) as exc_info:
        git_client.get_commits_by_author("2024-03-14", "2024-03-15", "test@example.com")
    assert str(exc_info.value) == "Git command failed"

@patch('subprocess.check_output')
def test_get_commit_branches_success(mock_check_output, git_client):
    mock_check_output.return_value = b"* develop\n  feature/test"
    result = git_client.get_commit_branches("abc123")
    assert result == ["develop", "feature/test"]
    mock_check_output.assert_called_once()

@patch('subprocess.check_output')
def test_get_commit_branches_failure(mock_check_output, git_client):
    mock_check_output.side_effect = Exception("Git command failed")
    with pytest.raises(Exception) as exc_info:
        git_client.get_commit_branches("abc123")
    assert str(exc_info.value) == "Git command failed"

@patch('subprocess.check_output')
def test_get_develop_commits_success(mock_check_output, git_client):
    mock_check_output.return_value = b"abc123\ndef456"
    result = git_client.get_develop_commits("2024-03-14", "2024-03-15", "test@example.com")
    assert result == {"abc123", "def456"}
    mock_check_output.assert_called_once()

@patch('subprocess.check_output')
def test_get_develop_commits_failure(mock_check_output, git_client):
    mock_check_output.side_effect = Exception("Git command failed")
    with pytest.raises(Exception) as exc_info:
        git_client.get_develop_commits("2024-03-14", "2024-03-15", "test@example.com")
    assert str(exc_info.value) == "Git command failed" 