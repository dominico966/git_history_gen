import pytest
from src.document_generator import DocumentGenerator
import tempfile
import git
import os

def test_document_generator():
    # Create a temporary git repo
    temp_dir = tempfile.mkdtemp()
    try:
        repo = git.Repo.init(temp_dir)
        # Create a file and commit
        with open(os.path.join(temp_dir, "test.txt"), "w") as f:
            f.write("test content")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")
        repo.close()  # Close the repo

        generator = DocumentGenerator(temp_dir)
        commits = generator.get_commits(limit=10)
        assert len(commits) == 1
        assert commits[0]["message"] == "Initial commit"
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
