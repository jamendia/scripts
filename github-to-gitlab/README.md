# GitHub to GitLab cloner with a wrapper.

## The script

It uses Git and Python 3 with the `requests` package.

### Features

- Accepts one or more GitHub repositories.
- Clones them as a bare repository, preserving branches and tags.
- Creates a new GitLab project automatically. 
- Pushes the complete repository to GitLab.
- Works on Linux and Windows (in principle...).
- Can optionally overwrite an existing GitLab project.
- Does not require GitHub CLI or GitLab CLI.

### Installation and basic use

If your Linux distribution prevents `pip --user`, use a virtual environment to install dependencies, 

```
python3 -m env ~/.config/gh2gl/env
python3 -m venv ~/.config/gh2gl/venv
~/.config/gh2gl/venv/bin/pip install requests
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

### What gets migrated?

The script uses `git clone --bare` followed by `git push --mirror`, so it tranfers the Git repository with branches, tags, commits and the complete history. It does not automatically migrate GitHub-specific features (such as Issues, Pull requests, GitHub Actions, Releases, Stars, etc.).

### Security detail

The script temporarily puts the access tokens into the Git HTTPS URLs used for clone/push. Git does not need credentials to be configured interactively, which makes the process easy to automate, but this is something to be aware of on shared machines. This could be fixed by using Git credential helpers or a temporary credential configuration so that tokens never appear in process arguments, etc. But I'm using it for myself, so use at your own peril.

## The wrapper

This small Bash wrapper is set up so that:

- can be invoked from anywhere as `gh2gl` (with the relevant config; see below),
- takes the repository as an argument: `gh2gl USERNAME/project-a`,
- asks for the GitHub repository if it is not provided,
- calls the script,
- checks that the two tokens exist before launching the Python script, and, if found,
- passes through your existing GITHUB_TOKEN and GITLAB_TOKEN environment variables.



