#!/usr/bin/env python3

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

import requests

class MigrationError(Exception):
    pass


def run_command(command, cwd=None):
    """Run a command and return its output."""
    print(f"\n> {' '.join(command)}")

    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    if result.returncode != 0:
        print(result.stdout)
        raise MigrationError(
            f"Command failed with exit code {result.returncode}"
        )

    return result.stdout


def check_git():
    if shutil.which("git") is None:
        raise MigrationError(
            "Git was not found in PATH. Install Git and try again."
        )


class GitHub:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://api.github.com"

    def get_repo(self, repo):
        """
        repo can be:
            owner/repository
            https://github.com/owner/repository
        """

        repo = repo.rstrip("/")

        if repo.startswith("https://github.com/"):
            repo = repo[len("https://github.com/"):]

        if repo.endswith(".git"):
            repo = repo[:-4]

        parts = repo.split("/")

        if len(parts) != 2:
            raise MigrationError(
                f"Invalid GitHub repository: {repo}. "
                "Expected owner/repository."
            )

        owner, name = parts

        response = requests.get(
            f"{self.base_url}/repos/{owner}/{name}",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=30,
        )

        if response.status_code != 200:
            raise MigrationError(
                f"Unable to access GitHub repository {repo}: "
                f"{response.status_code} {response.text}"
            )

        return response.json()


class GitLab:
    def __init__(self, token, url):
        self.token = token
        self.base_url = url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v4"

    def headers(self):
        return {
            "PRIVATE-TOKEN": self.token,
            "Content-Type": "application/json",
        }

    def find_namespace(self, namespace):
        """
        Returns the GitLab namespace/group ID.

        If namespace is omitted, the project will be created
        in the authenticated user's namespace.
        """

        if not namespace:
            return None

        # First try an exact path lookup.
        encoded = quote(namespace, safe="")

        response = requests.get(
            f"{self.api_url}/namespaces",
            headers=self.headers(),
            params={
                "search": namespace,
                "per_page": 100,
            },
            timeout=30,
        )

        if response.status_code != 200:
            raise MigrationError(
                f"Unable to find GitLab namespace '{namespace}': "
                f"{response.status_code} {response.text}"
            )

        namespaces = response.json()

        # Prefer an exact match.
        for item in namespaces:
            if item.get("full_path") == namespace:
                return item["id"]

        for item in namespaces:
            if item.get("path") == namespace:
                return item["id"]

        raise MigrationError(
            f"GitLab namespace/group '{namespace}' was not found."
        )

    def find_project(self, namespace, project_name):
        """Find an existing GitLab project."""

        path = (
            f"{namespace}/{project_name}"
            if namespace
            else project_name
        )

        encoded = quote(path, safe="")

        response = requests.get(
            f"{self.api_url}/projects/{encoded}",
            headers=self.headers(),
            timeout=30,
        )

        if response.status_code == 200:
            return response.json()

        if response.status_code == 404:
            return None

        raise MigrationError(
            f"Unable to query GitLab project '{path}': "
            f"{response.status_code} {response.text}"
        )

    def create_project(
        self,
        project_name,
        namespace_id=None,
        description=None,
        visibility="private",
    ):
        payload = {
            "name": project_name,
            "path": project_name,
            "visibility": visibility,
            "initialize_with_readme": False,
        }

        if description:
            payload["description"] = description

        if namespace_id:
            payload["namespace_id"] = namespace_id

        response = requests.post(
            f"{self.api_url}/projects",
            headers=self.headers(),
            json=payload,
            timeout=30,
        )

        if response.status_code not in (200, 201):
            raise MigrationError(
                f"Unable to create GitLab project '{project_name}': "
                f"{response.status_code} {response.text}"
            )

        return response.json()

    def delete_project(self, project_id):
        response = requests.delete(
            f"{self.api_url}/projects/{project_id}",
            headers=self.headers(),
            timeout=30,
        )

        if response.status_code not in (200, 202, 204):
            raise MigrationError(
                f"Unable to delete GitLab project {project_id}: "
                f"{response.status_code} {response.text}"
            )


def build_github_clone_url(repo, token):
    """
    Build an authenticated GitHub HTTPS URL.

    The token is only used by git during the clone operation.
    """

    repo = repo.rstrip("/")

    if repo.startswith("https://github.com/"):
        repo = repo[len("https://github.com/"):]

    if repo.endswith(".git"):
        repo = repo[:-4]

    # x-access-token is accepted by GitHub for HTTPS authentication.
    return f"https://x-access-token:{quote(token, safe='')}@github.com/{repo}.git"


def build_gitlab_push_url(project, token):
    """
    Build an authenticated GitLab HTTPS URL.
    """

    url = project["http_url_to_repo"]

    # GitLab accepts oauth2:<token> for HTTPS Git authentication.
    scheme, rest = url.split("://", 1)

    return (
        f"{scheme}://oauth2:"
        f"{quote(token, safe='')}"
        f"@{rest}"
    )


def migrate_repository(
    github,
    gitlab,
    repo_name,
    namespace,
    visibility,
    overwrite,
    work_dir,
):
    print("\n" + "=" * 70)
    print(f"Migrating: {repo_name}")
    print("=" * 70)

    repo_info = github.get_repo(repo_name)

    source_name = repo_info["name"]
    description = repo_info.get("description")

    # The GitLab project will use the same name by default.
    target_name = source_name

    if not target_name:
        raise MigrationError(
            f"Unable to determine repository name for {repo_name}"
        )

    print(f"GitHub : {repo_info['html_url']}")
    print(f"Project: {target_name}")

    existing = gitlab.find_project(namespace, target_name)

    if existing:
        print(
            f"GitLab project already exists: "
            f"{existing['web_url']}"
        )

        if not overwrite:
            raise MigrationError(
                f"Project already exists. Use --overwrite to replace it."
            )

        print("Deleting existing GitLab project...")
        gitlab.delete_project(existing["id"])

    namespace_id = gitlab.find_namespace(namespace)

    print("Creating GitLab project...")

    project = gitlab.create_project(
        project_name=target_name,
        namespace_id=namespace_id,
        description=description,
        visibility=visibility,
    )

    print(f"Created: {project['web_url']}")

    clone_url = build_github_clone_url(
        repo_name,
        github.token,
    )

    push_url = build_gitlab_push_url(
        project,
        gitlab.token,
    )

    repo_work_dir = Path(work_dir) / f"{target_name}.git"

    if repo_work_dir.exists():
        shutil.rmtree(repo_work_dir)

    try:
        print("Cloning GitHub repository...")

        run_command(
            [
                "git",
                "clone",
                "--bare",
                clone_url,
                str(repo_work_dir),
            ]
        )

        print("Pushing repository to GitLab...")

        run_command(
            [
                "git",
                "push",
                "--mirror",
                push_url,
            ],
            cwd=repo_work_dir,
        )

        print("\nMigration completed successfully.")
        print(f"GitLab repository: {project['web_url']}")

    finally:
        # Remove the temporary bare repository.
        if repo_work_dir.exists():
            shutil.rmtree(repo_work_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Migrate GitHub repositories to GitLab."
    )

    parser.add_argument(
        "repositories",
        nargs="+",
        help="GitHub repositories, e.g. owner/repository",
    )

    parser.add_argument(
        "--github-token",
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub Personal Access Token "
             "(or GITHUB_TOKEN environment variable)",
    )

    parser.add_argument(
        "--gitlab-token",
        default=os.environ.get("GITLAB_TOKEN"),
        help="GitLab Personal Access Token "
             "(or GITLAB_TOKEN environment variable)",
    )

    parser.add_argument(
        "--gitlab-url",
        default=os.environ.get(
            "GITLAB_URL",
            "https://gitlab.com",
        ),
        help="GitLab URL. Defaults to https://gitlab.com",
    )

    parser.add_argument(
        "--namespace",
        help=(
            "GitLab namespace/group. "
            "If omitted, uses the authenticated user's namespace."
        ),
    )

    parser.add_argument(
        "--visibility",
        choices=["private", "internal", "public"],
        default="private",
        help="GitLab project visibility. Defaults to private.",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Delete and recreate existing GitLab projects.",
    )

    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep temporary repositories after migration.",
    )

    args = parser.parse_args()

    if not args.github_token:
        parser.error(
            "GitHub token is required. "
            "Use --github-token or GITHUB_TOKEN."
        )

    if not args.gitlab_token:
        parser.error(
            "GitLab token is required. "
            "Use --gitlab-token or GITLAB_TOKEN."
        )

    check_git()

    if args.keep_temp:
        work_dir = Path.cwd() / "github-gitlab-migration"
        work_dir.mkdir(exist_ok=True)
        cleanup_work_dir = False
    else:
        temp_dir = tempfile.TemporaryDirectory()
        work_dir = Path(temp_dir.name)
        cleanup_work_dir = True

    github = GitHub(args.github_token)
    gitlab = GitLab(
        args.gitlab_token,
        args.gitlab_url,
    )

    failed = []

    try:
        for repository in args.repositories:
            try:
                migrate_repository(
                    github=github,
                    gitlab=gitlab,
                    repo_name=repository,
                    namespace=args.namespace,
                    visibility=args.visibility,
                    overwrite=args.overwrite,
                    work_dir=work_dir,
                )
            except Exception as exc:
                print(
                    f"\nERROR migrating {repository}: {exc}",
                    file=sys.stderr,
                )
                failed.append(repository)

    finally:
        if cleanup_work_dir:
            temp_dir.cleanup()

    print("\n" + "=" * 70)

    if failed:
        print("Migration completed with errors.")
        print("Failed repositories:")

        for repo in failed:
            print(f"  - {repo}")

        sys.exit(1)

    print("All repositories migrated successfully.")


if __name__ == "__main__":
    main()
