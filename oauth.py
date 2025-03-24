import webbrowser
import os
from dotenv import load_dotenv
load_dotenv()

CLIENT_ID: str = os.environ.get("CLIENT_ID")
redirect_uri = "http://localhost:4343/oauth/callback"

scopes = [
    "analytics:read:extensions",
    "analytics:read:games",
    "bits:read",
    "channel:edit:commercial",
    "channel:manage:broadcast",
    "channel:manage:extensions",
    "channel:manage:moderators",
    "channel:manage:polls",
    "channel:manage:predictions",
    "channel:manage:raids",
    "channel:manage:redemptions",
    "channel:manage:schedule",
    "channel:manage:videos",
    "channel:manage:vips",
    "channel:moderate",
    "channel:read:charity",
    "channel:read:editors",
    "channel:read:goals",
    "channel:read:hype_train",
    "channel:read:polls",
    "channel:read:predictions",
    "channel:read:redemptions",
    "channel:read:subscriptions",
    "channel:read:vips",
    "clips:edit",
    "moderation:read",
    "moderator:manage:announcements",
    "moderator:manage:automod",
    "moderator:manage:banned_users",
    "moderator:manage:blocked_terms",
    "moderator:manage:chat_messages",
    "moderator:manage:chat_settings",
    "moderator:manage:shoutouts",
    "moderator:read:automod_settings",
    "moderator:read:blocked_terms",
    "moderator:read:chat_settings",
    "user:edit",
    "user:edit:follows",
    "user:manage:blocked_users",
    "user:read:blocked_users",
    "user:read:broadcast",
    "user:read:email",
    "user:read:follows",
    "user:read:subscriptions",
    "whispers:read",
    "whispers:edit"
]
scope_str = "+".join(scopes)

oauth_url = f"https://id.twitch.tv/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={redirect_uri}&response_type=token&scope={scope_str}"

webbrowser.open(oauth_url)

print(
    f"Open this URL in your browser if it doesn't open automatically:\n{oauth_url}")
