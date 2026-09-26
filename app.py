import os
import re
import html
import streamlit as st
from supabase import create_client

# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="Clipsy",
    page_icon="✨",
    layout="centered",
)

SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
SUPABASE_KEY = st.secrets.get(
    "SUPABASE_PUBLISHABLE_KEY",
    os.getenv("SUPABASE_PUBLISHABLE_KEY", os.getenv("SUPABASE_ANON_KEY", "")),
)

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase is not configured.")
    st.code(
        '[supabase]\n'
        'url = "https://YOUR-PROJECT.supabase.co"\n'
        'publishable_key = "YOUR-PUBLISHABLE-KEY"',
        language="toml",
    )
    st.stop()

# Keep one client per Streamlit browser session.
if "supabase" not in st.session_state:
    st.session_state.supabase = create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
    )

supabase = st.session_state.supabase

# ============================================================
# HELPERS
# ============================================================

BLOCKED_TERMS = {
    "porn", "pornography", "nude", "nudes", "nsfw",
    "sexual", "sex", "drug", "drugs",
    "suicide", "selfharm",
}

BULLYING_PHRASES = {
    "kill yourself",
    "kys",
    "you are ugly",
    "you're ugly",
    "stupid",
    "loser",
}

def safe_text(value):
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", value.lower())
    text = re.sub(r"\s+", " ", text).strip()
    words = set(text.split())

    if words & BLOCKED_TERMS:
        return False, "This content doesn't meet our community guidelines."

    for phrase in BULLYING_PHRASES:
        if phrase in text:
            return False, "Please keep the community friendly and respectful."

    return True, ""


def esc(value):
    return html.escape(str(value))


def current_user():
    try:
        response = supabase.auth.get_user()
        return response.user
    except Exception:
        return None


def profile_for(user_id):
    result = (
        supabase.table("profiles")
        .select("*")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def profile_by_username(username):
    result = (
        supabase.table("profiles")
        .select("*")
        .eq("username", username)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def avatar_url(username):
    return f"https://i.pravatar.cc/150?u={username}"


def refresh():
    st.rerun()


# ============================================================
# STYLE
# ============================================================

st.markdown(
    """
<style>
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
header {visibility:hidden;}

.block-container {
    max-width: 700px;
    padding-top: 1rem;
    padding-bottom: 5rem;
}

.logo {
    font-size: 31px;
    font-weight: 800;
    letter-spacing: -1.5px;
}

.muted {
    color: #777;
    font-size: 13px;
}

.post-user {
    font-weight: 700;
}

.story-name {
    text-align: center;
    font-size: 12px;
}

.profile-avatar {
    border-radius: 50%;
}
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# AUTH SCREEN
# ============================================================

user = current_user()

if user is None:
    st.markdown('<div class="logo">✨ Clipsy</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="muted">Create. Share. Discover.</div>',
        unsafe_allow_html=True,
    )
    st.write("")

    login_tab, signup_tab = st.tabs(["Log in", "Create account"])

    with login_tab:
        email = st.text_input(
            "Email",
            placeholder="you@example.com",
            key="login_email",
        )
        password = st.text_input(
            "Password",
            type="password",
            key="login_password",
        )

        if st.button(
            "Log in",
            type="primary",
            use_container_width=True,
        ):
            if not email or not password:
                st.warning("Enter your email and password.")
            else:
                try:
                    supabase.auth.sign_in_with_password(
                        {
                            "email": email.strip(),
                            "password": password,
                        }
                    )
                    st.success("Logged in!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")

        st.divider()
        st.caption("Forgot your password?")

        reset_email = st.text_input(
            "Email for password reset",
            key="reset_email",
        )

        if st.button("Send reset email", use_container_width=True):
            if not reset_email:
                st.warning("Enter your email.")
            else:
                try:
                    supabase.auth.reset_password_for_email(reset_email.strip())
                    st.success("If the email exists, a reset message will be sent.")
                except Exception as e:
                    st.error(f"Could not send reset email: {e}")

    with signup_tab:
        name = st.text_input(
            "Display name",
            placeholder="Your name",
            key="signup_name",
        )
        username = st.text_input(
            "Username",
            placeholder="yourusername",
            key="signup_username",
        )
        email = st.text_input(
            "Email",
            placeholder="you@example.com",
            key="signup_email",
        )
        password = st.text_input(
            "Password",
            type="password",
            key="signup_password",
        )
        password2 = st.text_input(
            "Confirm password",
            type="password",
            key="signup_password2",
        )

        if st.button(
            "Create account",
            type="primary",
            use_container_width=True,
        ):
            username_clean = username.strip().lower()

            if not name.strip():
                st.warning("Enter a display name.")
            elif not re.fullmatch(r"[a-z0-9_]{3,24}", username_clean):
                st.warning(
                    "Username must be 3–24 characters using letters, numbers, or underscores."
                )
            elif not email.strip():
                st.warning("Enter an email.")
            elif len(password) < 8:
                st.warning("Password must be at least 8 characters.")
            elif password != password2:
                st.warning("Passwords don't match.")
            else:
                try:
                    existing = (
                        supabase.table("profiles")
                        .select("id")
                        .eq("username", username_clean)
                        .limit(1)
                        .execute()
                    )

                    if existing.data:
                        st.error("That username is already taken.")
                    else:
                        response = supabase.auth.sign_up(
                            {
                                "email": email.strip(),
                                "password": password,
                            }
                        )

                        new_user = response.user

                        if new_user is None:
                            st.error("Account could not be created.")
                        elif response.session is None:
                            st.success(
                                "Account created. Check your email to confirm your account, "
                                "then come back and log in."
                            )
                        else:
                            supabase.table("profiles").insert(
                                {
                                    "id": new_user.id,
                                    "username": username_clean,
                                    "display_name": name.strip(),
                                    "bio": "✨ Creating good vibes.",
                                }
                            ).execute()

                            st.success("Account created!")
                            st.rerun()

                except Exception as e:
                    st.error(f"Sign-up failed: {e}")

    st.stop()

# ============================================================
# PROFILE SETUP
# ============================================================

profile = profile_for(user.id)

if profile is None:
    st.title("Finish your profile")

    name = st.text_input("Display name")
    username = st.text_input("Username").strip().lower()
    bio = st.text_area("Bio", placeholder="Tell people a little about you.")

    if st.button("Save profile", type="primary", use_container_width=True):
        if not re.fullmatch(r"[a-z0-9_]{3,24}", username):
            st.warning("Username must be 3–24 characters using letters, numbers, or underscores.")
        elif not name.strip():
            st.warning("Enter a display name.")
        else:
            try:
                existing = (
                    supabase.table("profiles")
                    .select("id")
                    .eq("username", username)
                    .limit(1)
                    .execute()
                )

                if existing.data:
                    st.error("That username is already taken.")
                else:
                    supabase.table("profiles").insert(
                        {
                            "id": user.id,
                            "username": username,
                            "display_name": name.strip(),
                            "bio": bio.strip(),
                        }
                    ).execute()
                    st.rerun()
            except Exception as e:
                st.error(f"Could not save profile: {e}")

    if st.button("Log out"):
        supabase.auth.sign_out()
        st.rerun()

    st.stop()

# ============================================================
# HEADER
# ============================================================

c1, c2 = st.columns([4, 1])

with c1:
    st.markdown('<div class="logo">✨ Clipsy</div>', unsafe_allow_html=True)

with c2:
    if st.button("↪", help="Log out"):
        supabase.auth.sign_out()
        st.rerun()

# ============================================================
# NAV
# ============================================================

page = st.radio(
    "Navigation",
    ["🏠 Home", "🔎 Explore", "➕ Create", "🎬 Clips", "👤 Profile"],
    horizontal=True,
    label_visibility="collapsed",
)

# ============================================================
# HOME
# ============================================================

if page == "🏠 Home":

    st.subheader("Stories")

    story_result = (
        supabase.table("profiles")
        .select("username,display_name")
        .limit(8)
        .execute()
    )

    if story_result.data:
        cols = st.columns(min(5, len(story_result.data)))

        for i, p in enumerate(story_result.data[:5]):
            with cols[i]:
                st.image(avatar_url(p["username"]), width=58)
                st.markdown(
                    f'<div class="story-name">{esc(p["display_name"])}</div>',
                    unsafe_allow_html=True,
                )

    st.divider()
    st.subheader("For you")

    posts_result = (
        supabase.table("posts")
        .select(
            "id,user_id,caption,image_url,created_at,profiles(username,display_name)"
        )
        .order("created_at", desc=True)
        .limit(30)
        .execute()
    )

    posts = posts_result.data or []

    if not posts:
        st.info("No posts yet. Create the first one!")
    else:
        for post in posts:

            owner = post.get("profiles") or {}
            username = owner.get("username", "")
            display_name = owner.get("display_name", username)

            st.markdown(
                f"""
                <div class="post-user">
                    {esc(display_name)}
                    <span class="muted">@{esc(username)}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if post.get("image_url"):
                st.image(
                    post["image_url"],
                    use_container_width=True,
                )

            st.markdown(
                f"**{esc(display_name)}** {esc(post.get('caption', ''))}"
            )

            likes = (
                supabase.table("likes")
                .select("user_id", count="exact")
                .eq("post_id", post["id"])
                .execute()
            )

            like_count = likes.count or 0

            already_liked = (
                supabase.table("likes")
                .select("post_id")
                .eq("post_id", post["id"])
                .eq("user_id", user.id)
                .limit(1)
                .execute()
            )

            liked = bool(already_liked.data)

            a, b, c = st.columns([1, 1, 5])

            with a:
                if st.button(
                    "❤️" if liked else "♡",
                    key=f"like_{post['id']}",
                ):
                    try:
                        if liked:
                            supabase.table("likes").delete().eq(
                                "post_id", post["id"]
                            ).eq("user_id", user.id).execute()
                        else:
                            supabase.table("likes").insert(
                                {
                                    "post_id": post["id"],
                                    "user_id": user.id,
                                }
                            ).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not update like: {e}")

            with b:
                if st.button(
                    "🔖",
                    key=f"save_{post['id']}",
                ):
                    saved = (
                        supabase.table("saved_posts")
                        .select("post_id")
                        .eq("post_id", post["id"])
                        .eq("user_id", user.id)
                        .limit(1)
                        .execute()
                    )

                    if saved.data:
                        supabase.table("saved_posts").delete().eq(
                            "post_id", post["id"]
                        ).eq("user_id", user.id).execute()
                    else:
                        supabase.table("saved_posts").insert(
                            {
                                "post_id": post["id"],
                                "user_id": user.id,
                            }
                        ).execute()

                    st.rerun()

            st.caption(f"{like_count} likes")

            comments = (
                supabase.table("comments")
                .select("body,created_at,profiles(username,display_name)")
                .eq("post_id", post["id"])
                .order("created_at", desc=False)
                .limit(5)
                .execute()
            )

            for comment in comments.data or []:
                cp = comment.get("profiles") or {}
                st.caption(
                    f"💬 **{cp.get('display_name', 'User')}** {comment['body']}"
                )

            comment_text = st.text_input(
                "Add a comment",
                key=f"comment_{post['id']}",
                placeholder="Keep it friendly...",
            )

            if st.button(
                "Comment",
                key=f"comment_button_{post['id']}",
            ):
                if not comment_text.strip():
                    st.warning("Write a comment first.")
                else:
                    safe, message = safe_text(comment_text)

                    if not safe:
                        st.warning(message)
                    else:
                        supabase.table("comments").insert(
                            {
                                "post_id": post["id"],
                                "user_id": user.id,
                                "body": comment_text.strip(),
                            }
                        ).execute()
                        st.rerun()

            st.divider()

# ============================================================
# EXPLORE
# ============================================================

elif page == "🔎 Explore":

    st.subheader("Explore")

    search = st.text_input(
        "Search",
        placeholder="Search creators or captions...",
    )

    posts_result = (
        supabase.table("posts")
        .select(
            "id,caption,image_url,profiles(username,display_name)"
        )
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    posts = posts_result.data or []

    query = search.lower().strip()

    for post in posts:
        owner = post.get("profiles") or {}
        username = owner.get("username", "")
        name = owner.get("display_name", "")

        searchable = (
            f"{username} {name} {post.get('caption', '')}"
        ).lower()

        if query and query not in searchable:
            continue

        if post.get("image_url"):
            st.image(
                post["image_url"],
                use_container_width=True,
            )

        st.markdown(
            f"**{esc(name)}** @{esc(username)}"
        )
        st.caption(post.get("caption", ""))

# ============================================================
# CREATE
# ============================================================

elif page == "➕ Create":

    st.subheader("Create a post")

    st.info(
        "Share creative, positive content. Posts containing prohibited "
        "text are blocked by the basic safety filter."
    )

    image = st.file_uploader(
        "Choose an image",
        type=["jpg", "jpeg", "png", "webp"],
    )

    caption = st.text_area(
        "Caption",
        placeholder="What's happening? ✨",
    )

    if image:
        st.image(image, use_container_width=True)

    if st.button(
        "Share post",
        type="primary",
        use_container_width=True,
    ):

        if not image:
            st.warning("Choose an image.")
        elif not caption.strip():
            st.warning("Add a caption.")
        else:

            safe, message = safe_text(caption)

            if not safe:
                st.error(message)
            else:
                try:
                    # Store uploads in Supabase Storage.
                    filename = (
                        f"{user.id}/{__import__('uuid').uuid4().hex}"
                        f"_{re.sub(r'[^a-zA-Z0-9._-]', '_', image.name)}"
                    )

                    file_bytes = image.getvalue()

                    supabase.storage.from_("post-images").upload(
                        filename,
                        file_bytes,
                        {
                            "content-type": image.type,
                            "upsert": "false",
                        },
                    )

                    public_url = (
                        supabase.storage
                        .from_("post-images")
                        .get_public_url(filename)
                    )

                    supabase.table("posts").insert(
                        {
                            "user_id": user.id,
                            "caption": caption.strip(),
                            "image_url": public_url,
                        }
                    ).execute()

                    st.success("Posted! 🎉")
                    st.rerun()

                except Exception as e:
                    st.error(
                        "Upload failed. Make sure the "
                        "'post-images' storage bucket exists and is configured correctly."
                    )
                    st.code(str(e))

# ============================================================
# CLIPS
# ============================================================

elif page == "🎬 Clips":

    st.subheader("Clips")
    st.caption("Short creative videos.")

    st.info(
        "The Clips section is ready for video storage. "
        "For production, add a private/public Supabase Storage bucket "
        "and a clips table."
    )

    st.markdown("### Coming into the database-backed version")

    st.write("🎬 Upload short videos")
    st.write("❤️ Likes")
    st.write("💬 Comments")
    st.write("🔖 Saves")
    st.write("🛡️ Moderation")

# ============================================================
# PROFILE
# ============================================================

elif page == "👤 Profile":

    st.subheader("Profile")

    p = profile_for(user.id)

    if p:

        c1, c2 = st.columns([1, 3])

        with c1:
            st.image(
                avatar_url(p["username"]),
                width=120,
            )

        with c2:
            st.markdown(
                f"### {esc(p['display_name'])}"
            )
            st.caption(
                f"@{esc(p['username'])}"
            )
            st.write(
                p.get("bio") or "✨ Creating good vibes."
            )

        my_posts = (
            supabase.table("posts")
            .select("id,caption,image_url,created_at")
            .eq("user_id", user.id)
            .order("created_at", desc=True)
            .execute()
        )

        st.divider()

        a, b, c = st.columns(3)

        with a:
            st.metric("Posts", len(my_posts.data or []))

        with b:
            following = (
                supabase.table("follows")
                .select("following_id", count="exact")
                .eq("follower_id", user.id)
                .execute()
            )
            st.metric("Following", following.count or 0)

        with c:
            likes = 0
            for post in my_posts.data or []:
                result = (
                    supabase.table("likes")
                    .select("post_id", count="exact")
                    .eq("post_id", post["id"])
                    .execute()
                )
                likes += result.count or 0

            st.metric("Likes", likes)

        st.divider()

        st.markdown("### Your posts")

        if not my_posts.data:
            st.info("You haven't posted anything yet.")
        else:
            for post in my_posts.data:
                st.image(
                    post["image_url"],
                    use_container_width=True,
                )
                st.caption(
                    post["caption"]
                )

        st.divider()

        with st.expander("Edit profile"):

            new_name = st.text_input(
                "Display name",
                value=p.get("display_name", ""),
            )

            new_bio = st.text_area(
                "Bio",
                value=p.get("bio", ""),
            )

            if st.button("Save profile"):

                supabase.table("profiles").update(
                    {
                        "display_name": new_name.strip(),
                        "bio": new_bio.strip(),
                    }
                ).eq("id", user.id).execute()

                st.success("Profile updated.")
                st.rerun()

# ============================================================
# FOOTER
# ============================================================

st.divider()
st.caption("✨ Clipsy • Create • Share • Discover")
