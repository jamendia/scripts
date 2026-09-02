# GitHub to GitLab cloner

It uses Python + Git CLI + GitHub/GitLab REST APIs. In principle it should run on both Linux and Windows; Git handles the actual repository transfer.

### Features

- Accepts one or more GitHub repositories.
- Clones them as a bare repository, preserving branches and tags.
- Creates a new GitLab project automatically. 
- Pushes the complete repository to GitLab.
- Supports private GitHub repositories and GitLab groups/namespaces.
- Works on Linux and Windows.
- Can optionally overwrite an existing GitLab project.
- Does not require GitHub CLI or GitLab CLI.

### Installation and basic use

You need Python 3.9+ and Git installed on both Linux and Windows. The only Python dependency is `requests`:

```
python -m pip install requests
```

On some Linux distributions you may use (it is advisable to use a virtual environment, as usual):

```
python3 -m pip install requests
```

Verify Git with `git --version`. Then create your personal tokens:

- A GitHub Personal Access Token with access to the repositories you want to migrate.
- A GitLab Personal Access Token with permission to create projects and push repositories.

For private repositories, the GitHub token needs appropriate repository read access. The GitLab token needs sufficient API/project permissions. Now set the tokens as environment variables and exectute. In Linux/macOS:

```
export GITHUB_TOKEN="github_token_here"
export GITLAB_TOKEN="gitlab_token_here"
python3 gh2gl.py USERNAME/project
```

In Windows the following should work in PowerShell:

```
$env:GITHUB_TOKEN = "github_token_here"
$env:GITLAB_TOKEN = "gitlab_token_here"
python github_to_gitlab.py mycompany/project-a
```

Using environment variables is preferable to putting tokens directly on the command line because they won't appear in your shell history.

### Migrating multiple repositories

You can pass multiple repositories:

```
python3 github_to_gitlab.py \
    USERNAME1/project-a \
    USERNAME2/project-b \
    USERNAME3/project-c
```

The script will create:

```text
GitHub
  company/project-a
          |
          v
GitLab
  project-a

GitHub
  company/project-b
          |
          v
GitLab
  project-b
Migrating into a GitLab group
```

For example:

```
python3 gh2gl.py USERNAME1/project-a \
    --namespace my-gitlab-group
```

The resulting project will be `my-gitlab-group/project-a`.

### What gets migrated?

The script uses `git clone --bare` followed by `git push --mirror`, so it tranfers the Git repository's, including branches, tags, commits and the complete history. It does not automatically migrate GitHub-specific features (such as Issues, Pull requests, GitHub Actions, Releases, Stars, etc.). Those would require API-level migration separately.

### Security detail

The script temporarily puts the access tokens into the Git HTTPS URLs used for clone/push. Git does not need credentials to be configured interactively, which makes the process easy to automate, but this is something to be aware of on shared machines. This could be fixed by using Git credential helpers or a temporary credential configuration so tokens never appear in process arguments, etc. But I'm using it for myself, so use at your own peril.