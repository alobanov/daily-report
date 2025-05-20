import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, mock_open
from git_daily_report import ReportGenerator, GitConfig, GitClient, ChatGPTClient

@pytest.fixture
def git_config():
    return GitConfig(
        repo_path="/test/repo",
        author_email="test@example.com",
        target_date=datetime(2024, 3, 14)
    )

@pytest.fixture
def report_generator(git_config):
    with patch('git_daily_report.GitClient'), patch('git_daily_report.ChatGPTClient'):
        return ReportGenerator(git_config)

def test_load_prompt_template_success(report_generator):
    mock_template = "Test template {commits_text}"
    with patch('builtins.open', mock_open(read_data=mock_template)):
        result = report_generator.load_prompt_template()
        assert result == mock_template

def test_load_prompt_template_failure(report_generator):
    with patch('builtins.open', mock_open()) as mock_file:
        mock_file.side_effect = FileNotFoundError()
        with pytest.raises(SystemExit):
            report_generator.load_prompt_template()

@patch('git_daily_report.GitClient')
def test_collect_commits_info_no_commits(mock_git_client, report_generator):
    # Mock GitClient methods
    mock_git_client.return_value.get_username.return_value = "Test User"
    mock_git_client.return_value.get_commits_by_author.return_value = []
    mock_git_client.return_value.get_develop_commits.return_value = set()
    
    result = report_generator.collect_commits_info("Test User")
    assert result == ["🔀 Branch: develop", ""]

@patch('git_daily_report.GitClient')
def test_collect_commits_info_with_commits(mock_git_client, git_config):
    # Mock GitClient methods
    mock_git_client.return_value.get_username.return_value = "Test User"
    mock_git_client.return_value.get_commits_by_author.return_value = ["abc123", "def456"]
    mock_git_client.return_value.get_develop_commits.return_value = {"abc123"}
    mock_git_client.return_value.get_commit_branches.side_effect = lambda h: ["develop"] if h == "abc123" else ["feature/test"]
    mock_git_client.return_value.get_commit_details.side_effect = lambda h: f"* {h} 2024-03-14 Test commit"

    report_generator = ReportGenerator(git_config)
    result = report_generator.collect_commits_info("Test User")
    assert "🔀 Branch: develop" in result
    assert "* abc123 2024-03-14 Test commit" in result
    assert "🔀 Branch: feature/test" in result
    assert "* def456 2024-03-14 Test commit" in result

@patch('git_daily_report.GitClient')
@patch('git_daily_report.ChatGPTClient')
def test_generate_report_without_gpt(mock_chatgpt, mock_git_client, report_generator):
    # Mock GitClient methods
    mock_git_client.return_value.get_username.return_value = "Test User"
    mock_git_client.return_value.get_commits_by_author.return_value = ["abc123"]
    mock_git_client.return_value.get_develop_commits.return_value = set()
    mock_git_client.return_value.get_commit_branches.return_value = ["feature/test"]
    mock_git_client.return_value.get_commit_details.return_value = "* abc123 2024-03-14 Test commit"
    
    # Mock prompt template
    with patch('builtins.open', mock_open(read_data="Test template {commits_text}")):
        report_generator.generate_report(use_gpt=False)
        mock_chatgpt.return_value.generate_report.assert_not_called()

@patch('git_daily_report.GitClient')
@patch('git_daily_report.ChatGPTClient')
def test_generate_report_with_gpt(mock_chatgpt, mock_git_client, git_config):
    # Mock GitClient methods
    mock_git_client.return_value.get_username.return_value = "Test User"
    mock_git_client.return_value.get_commits_by_author.return_value = ["abc123"]
    mock_git_client.return_value.get_develop_commits.return_value = set()
    mock_git_client.return_value.get_commit_branches.return_value = ["feature/test"]
    mock_git_client.return_value.get_commit_details.return_value = "* abc123 2024-03-14 Test commit"

    # Mock ChatGPT response
    mock_chatgpt.return_value.generate_report.return_value = "Generated report"

    report_generator = ReportGenerator(git_config)
    with patch('builtins.open', mock_open(read_data="Test template {commits_text}")):
        report_generator.generate_report(use_gpt=True)
        mock_chatgpt.return_value.generate_report.assert_called_once() 