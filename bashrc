# if not running interactively, don't do anything
[ -z "$PS1" ] && return

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# 1. Custom prompt functions
# --------------------------------------------------------------
function git_branch() {
    if [ -d .git ]; then
        echo -n " ( " && git branch 2>/dev/null | grep '^*' | colrm 1 2 | tr -d '\n' && echo -n ")"
    fi
}

function git_stats() {
    local STATUS=$(git status -s 2> /dev/null)
    local ADDED=$(echo "$STATUS" | grep '??' | wc -l)
    local DELETED=$(echo "$STATUS" | grep ' D' | wc -l)
    local MODIFIED=$(echo "$STATUS" | grep ' M' | wc -l)
    local STATS=''
    if [ "$ADDED" -ne 0 ]; then
        STATS="\e[90;42m $ADDED "
    fi
    if [ "$DELETED" -ne 0 ]; then
        STATS="$STATS\e[101m $DELETED "
    fi
    if [ "$MODIFIED" -ne 0 ]; then
        STATS="$STATS\e[30;103m $MODIFIED "
    fi
    echo -e "\e[0m    $STATS\e[0m"
}

function origin_dist() {
    local STATUS="$(git status 2> /dev/null)"
    local DIST_STRING=""
    local IS_AHEAD=$(echo -n "$STATUS" | grep "ahead")
    local IS_BEHIND=$(echo -n "$STATUS" | grep "behind")
    if [ ! -z "$IS_AHEAD" ]; then
        local DIST_VAL=$(echo "$IS_AHEAD" | sed 's/[^0-9]*//g')
        DIST_STRING=" $DIST_VAL ▶"
    elif [ ! -z "$IS_BEHIND" ]; then
        local DIST_VAL=$(echo "$IS_BEHIND" | sed 's/[^0-9]*//g')
        DIST_STRING="◀ $DIST_VAL "
    fi
    if [ ! -z "$DIST_STRING" ]; then
        echo -en "\e[1;7m $DIST_STRING "
    fi
}

function virtualenv_info() {
    if [[ -n "$VIRTUAL_ENV" ]]; then
        venv="${VIRTUAL_ENV##*/}"
    else
        venv=''
    fi
    [[ -n "$venv" ]] && echo "\[\e[31;m\](venv:$venv)\[\e[0m\] "
}
export VIRTUAL_ENV_DISABLE_PROMPT=1

# 2. Complete Prompt Builder via PROMPT_COMMAND
# --------------------------------------------------------------
function set_my_prompt() {
    # CRITICAL: This MUST be the first command to capture the real exit code
    local LAST_EXIT=$?

    # Dynamically extract values
    local venv_part=$(virtualenv_info)
    local branch_part=$(git_branch)
    local stats_part=$(git_stats)
    local dist_part=$(origin_dist)

    # Pick the status icon with proper terminal-safe cursor tracking wrappers \[ \]
    local status_icon=""
    if [ "$LAST_EXIT" -eq 0 ]; then
        status_icon="\[\e[32;1m\]\[\e[0m\] "
    else
        status_icon="\[\e[31;1m\]✘\[\e[0m\] "
    fi

    # Assemble your structure cleanly into PS1 without splitting bugs
    # Line 1: Newline, Username, Path, and Git/Venv components
    PS1="\n\[\e[34m\]:\u \w\[\e[0m\]"
    [[ -n "$branch_part" ]] && PS1+="\[\e[35m\]${branch_part}\[\e[0m\]"
    [[ -n "$stats_part" ]]  && PS1+=" ${stats_part}"
    [[ -n "$dist_part" ]]   && PS1+=" ${dist_part}"
    [[ -n "\[\e[31;m\]$venv_part\[\e[0m\]" ]]   && PS1+="\[\e[31;m\]${venv_part}\[\e[0m\]"

    # Line 2: Inserts a newline right before the prompt status icon
    PS1+="\n${status_icon}"
}

# Instruct Bash to cleanly recreate the prompt every time you hit Enter
PROMPT_COMMAND=set_my_prompt

# aliases & helpers
if [ -f ~/.bash_aliases ]; then source ~/.bash_aliases; fi
if [ -f ~/.bash_functions ]; then source ~/.bash_functions; fi

export PATH=$PATH:~/scripts

[ -f "/home/ro/.ghcup/env" ] && . "/home/ro/.ghcup/env"
export PATH="$HOME/scripts:$PATH"
export PATH="$HOME/scripts/github-to-gitlab:$PATH"
