#!/usr/bin/env python

import os
import subprocess
import time
import configparser

import threading
import pystray
from PIL import Image, ImageDraw, ImageFont
from gi.repository import Gtk, GObject

# Get the username from the ~/.gitconfig file
def get_git_username():
    config = configparser.ConfigParser()
    config.read(os.path.expanduser('~/.gitconfig'))

    if 'user' in config and 'name' in config['user']:
        return config['user']['name']
    else:
        raise ValueError("Username not found in ~/.gitconfig")

# Get the current working directory
repo_path = os.getcwd()

# Get the username from the ~/.gitconfig file
user_to_monitor = get_git_username()


# A function to check if the latest commit is made by the user you want to monitor
def is_last_commit_by_user(username):
    try:
        output = subprocess.check_output(['git', 'log', '-1', '--pretty=format:%an'], cwd=repo_path)
        author_name = output.decode("utf-8")
        return author_name == username
    except Exception as e:
        print(f"Error checking last commit author: {e}")
        return False

def is_last_commit_unsigned():
    try:
        output = subprocess.check_output(['git', 'log', '-1', '--pretty=format:%G?'], cwd=repo_path)
        signature_status = output.decode("utf-8")
        print("Signature status: ", signature_status)
        return signature_status == "N"
    except Exception as e:
        print(f"Error checking last commit signature: {e}")
        return False


def get_current_branch_name(repo_path):
    branch_name = subprocess.check_output(['git', 'symbolic-ref', '--short', 'HEAD'], cwd=repo_path).decode("utf-8").strip()
    return branch_name

def get_remote_branch_name(local_branch_name):
    remote_repo_name = "origin"
    remote_branch_name = f"{remote_repo_name}/{local_branch_name}"
    return remote_branch_name

def is_commit_in_remote_branch(commit_hash, repo_path):
    branches = subprocess.check_output(['git', 'branch', '--contains', commit_hash, '--remote'], cwd=repo_path).decode("utf-8").strip()
    return bool(branches)

# A function to run the `git commit -S --amend --no-edit` command
def sign_commit():
    try:
        subprocess.check_call(['git', 'commit', '-S', '--amend', '--no-edit'], cwd=repo_path)
        print("Commit signed successfully.")
    except Exception as e:
        print(f"Error signing commit: {e}")




# The main function that monitors the git repository
def main():
    print("Monitoring git repository...")

    # Get the initial commit hash
    prev_commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo_path).decode("utf-8").strip()

    while True:
        try:
            # Check the current commit hash
            curr_commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo_path).decode("utf-8").strip()

            # If the commit hash changed, check if the last commit was made by the user to monitor
            if curr_commit_hash != prev_commit_hash:
                print("New commit detected.")
                prev_commit_hash = curr_commit_hash

                if is_last_commit_by_user(user_to_monitor):
                    if is_last_commit_unsigned():
                        if not is_commit_in_remote_branch(curr_commit_hash, repo_path):
                            print(f"Last commit made by {user_to_monitor}. Signing the commit...")
                            sign_commit()
                        else:
                            print(f"Last commit made by {user_to_monitor}. Commit is already pushed to remote. Ignoring the commit.")
                    else:
                        print(f"Last commit made by {user_to_monitor}. Commit already signed. Ignoring the commit.")
                else:
                    print(f"Last commit not made by {user_to_monitor}. Ignoring the commit.")
            
            # Wait for 10 seconds before checking the repository again
            time.sleep(1)
        except Exception as e:
            print(f"Error while monitoring repository: {e}")


def threaded_main():
    try:
        main()
    except Exception as e:
        print(f"Error while running main function: {e}")

# Function to start monitoring the repository
def start_monitoring(icon, item):
    icon.stop()
    thread = threading.Thread(target=threaded_main)
    thread.daemon = True
    thread.start()

# Function to stop the script
def stop_script(icon, item):
    icon.stop()
    exit(0)
    

# Function to create and display the system tray icon
def create_tray_icon():
    # Render a Unicode symbol as an icon image
    font_size = 48
    font = ImageFont.truetype("DejaVuSans.ttf", font_size)
    text = "✍️"
    (_, _,text_width, text_height) = font.getbbox(text)
    icon_image = Image.new("RGBA", (text_width, text_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(icon_image)
    draw.text((0, 0), text, font=font, fill=(255, 255, 0, 255))  # Use yellow color

    # Create a system tray icon
    icon = pystray.Icon("git_commit_monitor")

    # Create a context menu with a "Quit" option
    menu = (
        pystray.MenuItem("Quit", stop_script),
    )
    icon.menu = menu

    # Run the system tray icon
    icon.icon = icon_image

    # Start monitoring in a separate thread right after creating the tray icon
    thread = threading.Thread(target=threaded_main)
    thread.daemon = True
    thread.start()

    icon.run()

if __name__ == "__main__":
    create_tray_icon()
    Gtk.main()