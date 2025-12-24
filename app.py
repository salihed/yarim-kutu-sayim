import streamlit as st
from supabase import create_client
from datetime import datetime

# ----------------------------------------
# CONFIG
# ----------------------------------------
st.set_page_config(page_title="Adres Sayım", layout="centered")

# ----------------------------------------
# SUPABASE CONNECTION
# ----------------------------------------
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# ----------------------------------------
# SESSION STATE
# ----------------------------------------
if "address" not in st.session_state:
    st.session_state.address = None

if "current_unit" not in st.session_state:
    st.session_state.current_unit = None

# ----------------------------------------
# HELPERS
# ----------------------------------------
def get_progress(address):
    total = supabase.table("stock_units") \
        .select("id", count="exact") \
        .eq("address", address) \
        .execute().count

    counted = supabase.table("stock_units") \
        .select("id", count="exact") \
        .eq("address", address) \
        .eq("counted", True) \
        .execute().count

    return counted, total


def reset_address():
    st.session_state.address = None
    st.session_state.current_unit = None
    st.rerun()


# ----------------------------------------
# UI
# ----------------------------------------
st.title("📦 Adres Sayım Uygulaması")

# ----------------------------------------
# 1️⃣ ADRES OKUTMA
# ----------------------------------------
if st.session_state.address is None:
    st.subheader("Adres Okut")

    address = st.text_input("Adres Barkodu")

    if address:
        check = supabase.table("stock_units") \
            .select("id") \
            .eq("address", address) \
            .limit(1) \
            .execute()

        if len(check.data) == 0:
            st.error("❌ Bu adrese ait kayıt bulunamadı")
        else:
            st.session_state.address = address
            st.rerun()

    st.stop()

# ----------------------------------------
# 2️⃣ ADRES BİLGİSİ
# ----------------------------------------
counted, total = get_progress(st.session_state.address)

st.success(f"📍 Adres: {st.session_state.address}")
st.metric("İlerleme", f"{counted} / {total}")

# ----------------------------------------
# 3️⃣ HU OKUTMA
# ----------------------------------------
st.subheader("Taşıma Birimi Okut")

hu = st.text_input("HU Barkodu")

if hu:
    result = supabase.table("stock_units") \
        .select("*") \
        .eq("address", st.session_state.address) \
        .eq("handling_unit", hu) \
        .eq("counted", False) \
        .execute()

    if len(result.data) == 0:
        st.error("❌ Bu HU adreste tanımlı değil veya daha önce sayıldı")
        st.warning("👉 Kenara ayırın")
    else:
        st.session_state.current_unit = result.data[0]

# ----------------------------------------
# 4️⃣ BULUNAN HU DETAY
# ----------------------------------------
if st.session_state.current_unit:
    unit = st.session_state.current_unit

    st.info("🔍 Bulunan Taşıma Birimi")
    st.write(f"**Malzeme:** {unit['material']}")
    st.write(f"**Lot:** {unit['lot']}")
    st.write(f"**Miktar:** {unit['qty']}")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ BU"):
            supabase.table("stock_units").update({
                "counted": True,
                "status": "ok",
                "counted_at": datetime.utcnow()
            }).eq("id", unit["id"]).execute()

            st.session_state.current_unit = None
            st.rerun()

    with col2:
        if st.button("❌ DEĞİL"):
            st.session_state.current_unit = None
            st.warning("Lütfen doğru HU'yu okutun")

# ----------------------------------------
# 5️⃣ ADRESİ TAMAMLAMA
# ----------------------------------------
st.divider()

if st.button("📌 Adres Kontrolü Bitti"):
    missing = supabase.table("stock_units") \
        .select("id") \
        .eq("address", st.session_state.address) \
        .eq("counted", False) \
        .execute()

    if len(missing.data) > 0:
        ids = [x["id"] for x in missing.data]

        supabase.table("stock_units").update({
            "status": "missing"
        }).in_("id", ids).execute()

        st.warning(f"⚠️ {len(ids)} adet taşıma birimi BULUNAMADI olarak işaretlendi")

    st.success("✅ Adres tamamlandı")
    st.button("➡️ Yeni Adrese Geç", on_click=reset_address)
