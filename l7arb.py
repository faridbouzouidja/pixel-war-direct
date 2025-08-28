# pixel_war_helper.py
# Streamlit dashboard for wplace Pixel War: accounts, timers, advice, and PNG pixel counter
# Run: streamlit run pixel_war_helper.py

import json
from datetime import timedelta
from typing import List, Dict

import numpy as np
from PIL import Image
import streamlit as st

# -------------------------
# ---- App configuration ---
# -------------------------
st.set_page_config(
    page_title="EL 7ARB",
    page_icon="🎨",
    layout="wide"
)

# ---------- Styles ----------
DARK_CSS = """
<style>
/* overall */
.block-container {padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1200px;}
/* cards */
.px-card {background:#14161a; border:1px solid #2b2f36; padding:16px; border-radius:16px; box-shadow: 0 2px 10px rgba(0,0,0,.25);}
.px-title {font-size:1.1rem; font-weight:700; color:#e7e3ff; margin-bottom:.25rem;}
.px-sub {font-size:.85rem; color:#bfb8d6; margin-bottom:.75rem;}
/* tags / badges */
.px-badge {display:inline-block; background:#3b3551; color:#e7e3ff; padding:2px 8px; border-radius:999px; font-size:.75rem; margin-right:6px;}
/* lists */
.px-kv {display:flex; justify-content:space-between; padding:6px 10px; background: #1a1d22; border:1px solid #2b2f36; border-radius:10px; margin:.25rem 0;}
.px-kv span {font-size:.95rem; color:#e7e3ff;}
.px-kv small {color:#bfb8d6;}
/* buttons spacing */
button[kind="secondaryFormSubmit"] {margin-top: 6px;}
/* headings */
h1, h2, h3 {color:#f0edff;}
/* inputs */
.stNumberInput input, .stTextInput input {background:#1a1d22; color:#e7e3ff; border:1px solid #2b2f36;}
/* tables */
.stDataFrame {border-radius: 12px; overflow: hidden; border:1px solid #2b2f36;}
/* images box */
.px-imgbox {background:#1a1d22; border:1px dashed #3b3f46; border-radius: 16px; min-height:280px; display:flex; align-items:center; justify-content:center;}
</style>
"""
st.markdown(DARK_CSS, unsafe_allow_html=True)

# -------------------------
# ---- Session storage ----
# -------------------------
if "accounts" not in st.session_state:
    # Each account: {id, name, current, max}
    st.session_state.accounts: List[Dict] = []
if "next_id" not in st.session_state:
    st.session_state.next_id = 1
if "cooldown" not in st.session_state:
    st.session_state.cooldown = 30  # seconds / charge (global)
if "image_stats" not in st.session_state:
    st.session_state.image_stats = {"pixels": 0}

# -------------------------
# ---- Helper functions ----
# -------------------------
def seconds_to_hms_str(s: float) -> str:
    if s < 0:
        s = 0
    return str(timedelta(seconds=int(round(s))))

def time_to_full(acc, cooldown: int) -> int:
    """seconds until full for one account"""
    missing = max(acc["max"] - acc["current"], 0)
    return missing * cooldown

def totals():
    total_current = sum(a["current"] for a in st.session_state.accounts)
    total_max = sum(a["max"] for a in st.session_state.accounts)
    return total_current, total_max

def advice_equalize_times(cooldown: int):
    """
    Compute an 'equalization' plan so all accounts become full at the same time.
    We take T* = max(time_to_full_i). For faster accounts, advise to spend some
    charges now to increase their time_to_full to T*.
    Return: list of dict per account with keys: target_current, use_now
    """
    if not st.session_state.accounts:
        return [], 0

    times = [time_to_full(a, cooldown) for a in st.session_state.accounts]
    Tstar = max(times)  # align to the slowest

    plan = []
    for a in st.session_state.accounts:
        target_current = max(a["max"] - Tstar // cooldown, 0)
        # We cannot increase current; if target_current > current, use_now=0
        use_now = max(a["current"] - target_current, 0)
        plan.append({
            "id": a["id"],
            "name": a["name"],
            "current": a["current"],
            "max": a["max"],
            "target_current": int(target_current),
            "use_now": int(use_now),
            "time_to_full_now": time_to_full(a, cooldown)
        })
    return plan, Tstar

def count_nontransparent_pixels(img: Image.Image) -> int:
    """Counts pixels where alpha > 0. If no alpha channel, counts all pixels."""
    if img.mode in ("RGBA", "LA"):
        alpha = np.array(img.split()[-1])
        return int(np.count_nonzero(alpha > 0))
    # If palette with transparency
    if img.mode == "P":
        img = img.convert("RGBA")
        return count_nontransparent_pixels(img)
    # No alpha -> consider all pixels
    w, h = img.size
    return int(w * h)

def estimate_finish_time_for_image(num_pixels: int, cooldown: int) -> int:
    """
    Estimate time (seconds) to finish the drawing if an auto-placer consumes pixels
    as soon as they are available. Throughput ~= (N_accounts / cooldown) pixels/sec,
    starting with total_current pixels already available.
    """
    n_acc = len(st.session_state.accounts)
    total_current, _ = totals()
    if num_pixels <= total_current:
        return 0
    remaining = num_pixels - total_current
    if n_acc <= 0:
        return float("inf")
    rate = n_acc / cooldown  # pixels per second
    return int(np.ceil(remaining / rate))

# -------------------------
# ---- Header -------------
# -------------------------
left, mid, right = st.columns([1.25, 1.25, 1])

with left:
    st.markdown('<div class="px-card">', unsafe_allow_html=True)
    st.markdown('<div class="px-title">🎨 Rigel omoratek w odkhol t7areb</div>', unsafe_allow_html=True)
    st.caption("Wedjed ro7ek soldat")

    st.session_state.cooldown = 30

    st.markdown('<div class="px-sub">ajouti compte</div>', unsafe_allow_html=True)
    with st.form("add_account_form", clear_on_submit=True):
        name = st.text_input("wesh asmek ?", value="", max_chars=40)
        cc, mc = st.columns(2)
        with cc:
            cur = st.number_input("ch7al 3andek men charge rn ?", min_value=0, value=0, step=1)
        with mc:
            mx = st.number_input("wel max charges ch7al ?", min_value=1, value=100, step=1)
        submitted = st.form_submit_button("➕ f chbb ajoutih tchou")
        if submitted:
            st.session_state.accounts.append(
                {"id": st.session_state.next_id, "name": name or f"Account {st.session_state.next_id}",
                 "current": int(cur), "max": int(mx)}
            )
            st.session_state.next_id += 1
            st.success("Account added.")

    st.markdown("---")
    st.markdown('<div class="px-title">Accounts</div>', unsafe_allow_html=True)
    if not st.session_state.accounts:
        st.info("ajouti compte yer7am babak")
    else:
        # editable rows
        for acc in st.session_state.accounts:
            with st.container(border=True):
                st.markdown(f"**{acc['name']}**  "
                            f"<span class='px-badge'>ID {acc['id']}</span>",
                            unsafe_allow_html=True)
                c1, c2, c3 = st.columns([1, 1, 0.5])
                with c1:
                    new_cur = st.number_input(f"les charges te3ek (ID {acc['id']})", min_value=0, value=int(acc["current"]), key=f"cur_{acc['id']}")
                with c2:
                    new_max = st.number_input(f"Max charges li 3andek(ID {acc['id']})", min_value=1, value=int(acc["max"]), key=f"max_{acc['id']}")
                with c3:
                    st.write("")
                    st.write("")
                    if st.button("✅ savi stp", key=f"save_{acc['id']}"):
                        acc["current"] = int(new_cur)
                        acc["max"] = int(new_max)
                        st.success("Saved")
                # delete
                dcol, _ = st.columns([0.25, 0.75])
                with dcol:
                    if st.button("🗑️ deletih", key=f"del_{acc['id']}"):
                        st.session_state.accounts = [a for a in st.session_state.accounts if a["id"] != acc["id"]]
                        st.experimental_rerun()

    st.markdown('</div>', unsafe_allow_html=True)  # close card

with mid:
    st.markdown('<div class="px-card">', unsafe_allow_html=True)
    st.markdown('<div class="px-title">Per-account timers</div>', unsafe_allow_html=True)
    st.caption("time till tkoun full")

    if st.session_state.accounts:
        for acc in st.session_state.accounts:
            ttf = time_to_full(acc, st.session_state.cooldown)
            st.markdown(f"<div class='px-kv'><span>{acc['name']}</span><span>{seconds_to_hms_str(ttf)}</span></div>", unsafe_allow_html=True)
    else:
        st.info("ya khouya ajouti coooompte")

    st.markdown("---")
    st.markdown('<div class="px-title">LES STATS</div>', unsafe_allow_html=True)
    total_current, total_max = totals()
    all_full_seconds = max([time_to_full(a, st.session_state.cooldown) for a in st.session_state.accounts], default=0)

    c1, c2, c3 = st.columns(3)
    c1.metric("ch7al 3andek", f"{total_current}")
    c2.metric("ch7al tel7a9", f"{total_max}")
    c3.metric("ch7al testena full", seconds_to_hms_str(all_full_seconds))

    st.markdown("---")
    st.markdown('<div class="px-title">nethala fik</div>', unsafe_allow_html=True)
    if st.session_state.accounts:
        plan, Tstar = advice_equalize_times(st.session_state.cooldown)
        st.caption(f"Goal: les comptes ge3 ykono full at same time in ≈ **{seconds_to_hms_str(Tstar)}**.")
        if plan:
            for row in plan:
                # Only show advice when there's something to do
                if row["use_now"] > 0:
                    st.markdown(
                        f"<div class='px-kv'><span>Use **{row['use_now']} px** now from "
                        f"**{row['name']}**</span><small>target {row['target_current']}/{row['max']} "
                        f"(was {row['current']}/{row['max']})</small></div>",
                        unsafe_allow_html=True
                    )
            # If no moves needed:
            if all(r["use_now"] == 0 for r in plan):
                st.success("rake f chbab deja opti.")
        else:
            st.info("EL COMPTE AJOUTIH")
    else:
        st.info("EL COMPTE YA RAB EL COMPTE AJOUTIH")

    st.markdown('</div>', unsafe_allow_html=True)  # close card

with right:
    st.markdown('<div class="px-card">', unsafe_allow_html=True)
    st.markdown('<div class="px-title">pixels calculator</div>', unsafe_allow_html=True)
    st.caption("ma tensach t7on l png li khfif meshi 1080x1080")
    up_img = st.file_uploader("7ot tchou teswirtek", type=["png"])
    img = None
    if up_img is not None:
        try:
            img = Image.open(up_img)
            st.image(img, caption="Preview", use_column_width=True)
            px = count_nontransparent_pixels(img)
            st.session_state.image_stats["pixels"] = px
        except Exception as e:
            st.error(f"awah 7anouni ma 9dertch nloadiha chouf m3a farid code te3ou khéné: {e}")

    px = st.session_state.image_stats.get("pixels", 0)
    st.markdown(f"<div class='px-kv'><span>hahou ch7al fiha men pixel : </span><span>{px}</span></div>", unsafe_allow_html=True)

    # Estimate time to finish drawing
    if st.session_state.accounts and px > 0:
        est = estimate_finish_time_for_image(px, st.session_state.cooldown)
        if np.isinf(est):
            st.warning("Add at least one account to estimate finish time.")
        else:
            st.markdown(f"<div class='px-kv'><span>Estimated time to finish</span><span>{seconds_to_hms_str(est)}</span></div>", unsafe_allow_html=True)
            st.caption(
                "Estimation assumes an auto-placer draws continuously: "
                "you immediately spend current charges, then new pixels are placed as they recharge. "
                "Throughput ≈ N_accounts / cooldown."
            )
    elif px == 0:
        st.info("wesh nanalisi ida makach teswira ?")
    else:
        st.info("Add accounts to get finish-time estimation.")

    st.markdown('</div>', unsafe_allow_html=True)  # close card

