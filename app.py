import random
import re
import smtplib
import ssl
from email.message import EmailMessage

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Secret Santa", page_icon="🎅", layout="centered")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------- Helpers ----------
def draw_names(names):
    """Return a dict giver -> receiver where nobody gets themselves."""
    while True:
        receivers = names[:]
        random.shuffle(receivers)
        if all(g != r for g, r in zip(names, receivers)):
            return dict(zip(names, receivers))


def get_smtp_config():
    """Read SMTP settings from Streamlit secrets, with sidebar fallback."""
    cfg = {}
    try:
        cfg = dict(st.secrets.get("smtp", {}))
    except Exception:
        cfg = {}

    with st.sidebar:
        st.header("Email settings")
        if cfg:
            st.success("Email settings loaded from app secrets.")
        else:
            st.caption("Only needed if you want to send emails.")
            cfg["host"] = st.text_input("SMTP host", value="smtp.gmail.com")
            cfg["port"] = st.number_input("SMTP port", value=465, step=1)
            cfg["user"] = st.text_input("SMTP username (your email)")
            cfg["password"] = st.text_input("SMTP password / app password", type="password")
            cfg["from_name"] = st.text_input("Sender name", value="Secret Santa")
    return cfg


def send_emails(cfg, assignments, email_lookup, event_note):
    results = []
    host, port = cfg.get("host"), int(cfg.get("port", 465))
    user, password = cfg.get("user"), cfg.get("password")
    from_name = cfg.get("from_name", "Secret Santa")

    context = ssl.create_default_context()
    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, context=context, timeout=30)
        else:
            server = smtplib.SMTP(host, port, timeout=30)
            server.starttls(context=context)
        server.login(user, password)
    except Exception as e:
        return [("(all)", False, f"Could not connect/login: {e}")]

    with server:
        for giver, receiver in assignments.items():
            addr = email_lookup.get(giver)
            if not addr:
                results.append((giver, False, "No email address given"))
                continue
            msg = EmailMessage()
            msg["Subject"] = "🎅 Your Secret Santa assignment"
            msg["From"] = f"{from_name} <{user}>"
            msg["To"] = addr
            body = (
                f"Hi {giver},\n\n"
                f"You are the Secret Santa for: {receiver}\n\n"
                f"{event_note}\n"
                "Please keep it secret!\n\n"
                "Happy gifting! 🎁"
            )
            msg.set_content(body)
            try:
                server.send_message(msg)
                results.append((giver, True, f"Sent to {addr}"))
            except Exception as e:
                results.append((giver, False, str(e)))
    return results


# ---------- UI ----------
st.title("🎅 Secret Santa")
st.write(
    "Add everyone taking part below. Click the **+** row at the bottom of the table "
    "to add more people. Email addresses are optional."
)

if "table" not in st.session_state:
    st.session_state.table = pd.DataFrame(
        {"Name": ["", "", ""], "Email (optional)": ["", "", ""]}
    )

edited = st.data_editor(
    st.session_state.table,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Name": st.column_config.TextColumn("Name", required=False),
        "Email (optional)": st.column_config.TextColumn("Email (optional)"),
    },
    key="editor",
)

event_note = st.text_area(
    "Optional note to include in emails (budget, date, venue...)",
    placeholder="e.g. Budget R200. Gift exchange on 20 December at 6pm.",
)

if st.button("🎲 Draw names", type="primary"):
    rows = edited.fillna("").astype(str)
    people = []
    for _, row in rows.iterrows():
        name = row["Name"].strip()
        email = row["Email (optional)"].strip()
        if name:
            people.append((name, email))

    names = [p[0] for p in people]
    errors = []
    if len(names) < 2:
        errors.append("Please enter at least 2 names (3 or more is more fun).")
    if len({n.lower() for n in names}) != len(names):
        errors.append("Names must be unique. Add a surname or initial to tell people apart.")
    for name, email in people:
        if email and not EMAIL_RE.match(email):
            errors.append(f"Invalid email for {name}: {email}")

    if errors:
        for e in errors:
            st.error(e)
    else:
        st.session_state.assignments = draw_names(names)
        st.session_state.emails = {n: e for n, e in people if e}
        st.session_state.email_results = None

# ---------- Results (bottom of app) ----------
if st.session_state.get("assignments"):
    st.divider()
    st.subheader("Who is buying for whom")
    result_df = pd.DataFrame(
        {
            "Giver": list(st.session_state.assignments.keys()),
            "Buys a gift for": list(st.session_state.assignments.values()),
        }
    )
    st.table(result_df.set_index("Giver"))
    st.caption("Tip: if you're taking part yourself, don't scroll to this list before the draw is shared!")

    st.subheader("Email the assignments (optional)")
    with_email = [g for g in st.session_state.assignments if g in st.session_state.emails]
    if not with_email:
        st.info("No email addresses were entered, so there is nobody to email.")
    else:
        st.write(f"{len(with_email)} of {len(st.session_state.assignments)} people have an email address.")
        smtp_cfg = get_smtp_config()
        if st.button("📧 Send emails"):
            if not (smtp_cfg.get("host") and smtp_cfg.get("user") and smtp_cfg.get("password")):
                st.error("Please complete the email settings first.")
            else:
                with st.spinner("Sending..."):
                    st.session_state.email_results = send_emails(
                        smtp_cfg,
                        st.session_state.assignments,
                        st.session_state.emails,
                        event_note,
                    )

    if st.session_state.get("email_results"):
        for who, ok, info in st.session_state.email_results:
            (st.success if ok else st.error)(f"{who}: {info}")
