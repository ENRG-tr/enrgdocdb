import hashlib
import os
import subprocess

import requests

# --- Configuration ---
SERVER_TYPE = "cpu"  # "cpu" or "gpu"
API_TOKEN = "your_secret_token_here"
API_URL = (
    f"https://neutrino.erciyes.edu.tr/api/users/with-role/enrg-server-{SERVER_TYPE}"
)
RESEARCH_GROUP = "enrg_research"  # Local group to identify managed users


def get_md5_password(email):
    return hashlib.md5(email.encode()).hexdigest()[:5]


def generate_username(first_name, last_name):
    first = "".join(filter(str.isalnum, first_name[0].lower()))
    last = "".join(filter(str.isalnum, last_name[:6].lower()))
    return f"{first}{last}"


def get_local_managed_users():
    """Returns a list of usernames currently in the RESEARCH_GROUP."""
    try:
        # Get members of the group from /etc/group
        result = subprocess.run(
            ["getent", "group", RESEARCH_GROUP], capture_output=True, text=True
        )
        if result.returncode != 0:
            # Create group if it doesn't exist
            subprocess.run(["groupadd", RESEARCH_GROUP])
            return []

        line = result.stdout.strip()
        parts = line.split(":")
        if len(parts) > 3 and parts[3]:
            return parts[3].split(",")
        return []
    except Exception:
        return []


def sync_users():
    headers = {"Authorization": f"Bearer {API_TOKEN}"}

    try:
        response = requests.get(API_URL, headers=headers)
        response.raise_for_status()
        remote_users = response.json()
    except Exception as e:
        print(f"CRITICAL: Could not fetch from DocDB: {e}")
        return

    local_managed = get_local_managed_users()
    active_usernames = set()
    used_usernames = {}  # {username: email} for collision checking

    # Ensure the research group exists
    subprocess.run(["groupadd", "-f", RESEARCH_GROUP])

    # --- PHASE 1: Create & Update ---
    for user in remote_users:
        fname = user.get("first_name", "").strip()
        lname = user.get("last_name", "").strip()
        email = user.get("email", "").strip()

        if not all([fname, lname, email]):
            continue

        username = generate_username(fname, lname)

        # Collision Check: If username exists but email is different, suffix it
        if username in used_usernames and used_usernames[username] != email:
            counter = 1
            original_username = username
            while username in used_usernames:
                username = (
                    f"{original_username[:6]}{counter}"  # Shorten to allow suffix
                )
                counter += 1

        used_usernames[username] = email
        active_usernames.add(username)

        # Check if user already exists on the system
        user_exists = (
            subprocess.run(["id", username], capture_output=True).returncode == 0
        )

        if not user_exists:
            print(f"[NEW] Creating {username} ({email})...")
            password = get_md5_password(email)
            try:
                # Create user and add to the tracking group
                subprocess.run(
                    [
                        "useradd",
                        "-m",
                        "-g",
                        RESEARCH_GROUP,
                        "-s",
                        "/bin/bash",
                        username,
                    ],
                    check=True,
                )

                # Set password
                proc = subprocess.Popen(["chpasswd"], stdin=subprocess.PIPE, text=True)
                proc.communicate(input=f"{username}:{password}")

                # Force change on login
                subprocess.run(["chage", "-d", "0", username], check=True)
            except Exception as e:
                print(f"Error creating {username}: {e}")
        else:
            # Ensure existing user is in the research group if they were moved there
            subprocess.run(["usermod", "-aG", RESEARCH_GROUP, username])

    # --- PHASE 2: Cleanup ---
    # Find users who are in the local group but NOT in the latest DocDB fetch
    for local_user in local_managed:
        if local_user not in active_usernames:
            print(f"[CLEANUP] Locking account for {local_user} (Not in DocDB)")
            # We lock the account (L) and expire it (e 1) instead of deleting
            # so we don't destroy their research data/files accidentally.
            subprocess.run(["usermod", "-L", "-e", "1", local_user])


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Please run as root/sudo.")
    else:
        sync_users()
        print("Sync Complete.")
