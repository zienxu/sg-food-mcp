"""Streamlit app: photo -> estimate, drinks via tap list, log in session_state only."""
import sys
import tempfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
import data      # noqa: E402
import estimate  # noqa: E402

st.set_page_config(page_title="SG Food Log", page_icon="🍜")

if "log" not in st.session_state:
    st.session_state.log = []  # [{"dish": str, "kcal": int}, ...]


def add_entry(dish: str, kcal: int) -> None:
    st.session_state.log.append({"dish": dish, "kcal": kcal})


st.title("SG Food Log")

# ---- Photo -> estimate ----
st.header("Photo")
photo = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png"])

if photo is not None:
    photo_key = (photo.name, photo.size)
    if st.session_state.get("photo_key") != photo_key:
        suffix = Path(photo.name).suffix or ".jpg"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(photo.getvalue())
            tmp_path = tmp.name
        try:
            with st.spinner("Identifying..."):
                st.session_state.result = estimate.estimate(tmp_path)
            st.session_state.result_error = None
        except Exception as e:
            st.session_state.result = None
            st.session_state.result_error = str(e)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
        st.session_state.photo_key = photo_key

    if st.session_state.get("result_error"):
        st.error(f"Could not estimate this photo: {st.session_state.result_error}")
    else:
        result = st.session_state.get("result")
        if result:
            if result["question"]:
                st.info(result["question"])
            else:
                st.success(f"{result['dish']}: {result['kcal']} kcal")
                for a in result["assumptions"]:
                    st.caption(a)
                if st.button("Add to today's log", key="add_photo"):
                    add_entry(result["dish"], result["kcal"])

# ---- Drinks: tap list of favourites ----
st.header("Drinks")
favourites = [d for d in data.DISHES if d["is_favourite"] == "TRUE"]
cols = st.columns(3)
for i, d in enumerate(favourites):
    with cols[i % 3]:
        kcal = int(d["kcal_default"])
        if st.button(f"{d['dish_name']} ({kcal} kcal)", key=f"tap-{d['id']}"):
            add_entry(d["dish_name"], kcal)

# ---- Today's log ----
st.header("Today's log")
if st.button("Clear log", disabled=not st.session_state.log):
    st.session_state.log = []

if st.session_state.log:
    st.metric("Total kcal", sum(e["kcal"] for e in st.session_state.log))
    for e in st.session_state.log:
        st.write(f"- {e['dish']}: {e['kcal']} kcal")
else:
    st.write("No entries yet.")
