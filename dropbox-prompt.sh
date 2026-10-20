# dropbox-prompt.sh
#
# 
# This gist fetches Dropbox quota data, caches successful results for
# 300 seconds, and prints the used and allocated byte counts. 
# It contains no credentials; each person supplies their own.
#
# It requires curl and jq.
#
# Set DROPBOX_APP_KEY, DROPBOX_APP_SECRET, and DROPBOX_REFRESH_TOKEN
# in the shell before calling dropbox_prompt_quota. Then save it as
# dropbox-prompt.sh. To load it in the current shell, run
#
# > . "$HOME/path/to/dropbox-prompt.sh"
#
# or put it in the appropriate startup file (~/.bashrc, ~/.zshrc, etc.)
# and set your own credentials in the shell. On success, it prints 
# `used allocated` in bytes. The DROPBOX_PROMPT_DIR setting is available
# for the prompt code that decides when to show Dropbox information;
# this quota-fetching function itself doesn’t check the current 
# directory.

DROPBOX_PROMPT_DIR=${DROPBOX_PROMPT_DIR:-"$HOME/Dropbox"}
DROPBOX_PROMPT_CACHE=${DROPBOX_PROMPT_CACHE:-"${XDG_CACHE_HOME:-"$HOME/.cache"}/dropbox-prompt/quota"}
DROPBOX_PROMPT_QUOTA_TTL=${DROPBOX_PROMPT_QUOTA_TTL:-300}

dropbox_prompt_quota() (
    # Run in a subshell so temporary variables don't affect the caller.
    is_uint() {
        case $1 in
            ''|*[!0-9]*) return 1 ;;
            *) return 0 ;;
        esac
    }

    [ -n "${DROPBOX_APP_KEY:-}" ] &&
    [ -n "${DROPBOX_APP_SECRET:-}" ] &&
    [ -n "${DROPBOX_REFRESH_TOKEN:-}" ] || return 1

    case $DROPBOX_PROMPT_QUOTA_TTL in
        ''|*[!0-9]*) ttl=300 ;;
        *) ttl=$DROPBOX_PROMPT_QUOTA_TTL ;;
    esac

    now=$(date +%s) || return 1
    cache_file=$DROPBOX_PROMPT_CACHE

    # Use a cached result only while it's within the TTL.
    if [ -r "$cache_file" ]; then
        IFS=' ' read -r cached_at cached_used cached_allocated < "$cache_file"
        if is_uint "$cached_at" &&
           is_uint "$cached_used" &&
           is_uint "$cached_allocated" &&
           [ "$now" -ge "$cached_at" ]; then
            age=$((now - cached_at))
            if [ "$age" -lt "$ttl" ]; then
                printf '%s %s\n' "$cached_used" "$cached_allocated"
                return 0
            fi
        fi
    fi

    token_response=$(curl -fsS \
        --user "$DROPBOX_APP_KEY:$DROPBOX_APP_SECRET" \
        --data-urlencode 'grant_type=refresh_token' \
        --data-urlencode "refresh_token=$DROPBOX_REFRESH_TOKEN" \
        https://api.dropbox.com/oauth2/token 2>/dev/null) || return 1

    token=$(printf '%s\n' "$token_response" |
        jq -er '.access_token' 2>/dev/null) || return 1

    usage_response=$(curl -fsS -X POST \
        https://api.dropboxapi.com/2/users/get_space_usage \
        -H "Authorization: Bearer $token" \
        -H 'Content-Type: application/json' \
        --data 'null' 2>/dev/null) || return 1

    quota=$(printf '%s\n' "$usage_response" |
        jq -er '
            if (.used | type) == "number" and
               (.allocation.allocated | type) == "number"
            then "\(.used) \(.allocation.allocated)"
            else error("Missing quota fields")
            end
        ' 2>/dev/null) || return 1

    IFS=' ' read -r used allocated extra <<EOF
$quota
EOF
    is_uint "$used" && is_uint "$allocated" && [ -z "$extra" ] || return 1

    # Cache the successful response; if caching fails, still return the result.
    case $cache_file in
        */*) cache_dir=${cache_file%/*} ;;
        *) cache_dir=. ;;
    esac

    if mkdir -p -- "$cache_dir" 2>/dev/null; then
        tmp="${cache_file}.$$"
        if printf '%s %s %s\n' "$now" "$used" "$allocated" > "$tmp"; then
            mv -f -- "$tmp" "$cache_file" 2>/dev/null ||
                rm -f -- "$tmp"
        fi
    fi

    printf '%s %s\n' "$used" "$allocated"
)
