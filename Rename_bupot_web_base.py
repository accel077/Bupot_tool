import streamlit as st
import pdfplumber
import re
import io
import zipfile
import pandas as pd

# --- FUNGSI LOGIKA (Ekstrak Data dari PDF) ---
def extract_info(pdf_file):
    try:
        with pdfplumber.open(pdf_file) as pdf:
            full_text = pdf.pages[0].extract_text()
            if not full_text:
                return None, None, None
                
            lines = full_text.split('\n')
            nama, nomor_bupot, nomor_dokumen = "", "", ""
            
            for i, line in enumerate(lines):
                # 1. Cari Nama di identitas A.2
                if "A.2" in line:
                    nama = line.replace("A.2", "").replace("NAMA", "").replace(":", "").strip()
                
                # 2. Cari Nomor Bupot di bawah header NOMOR
                if "NOMOR" in line and "MASA PAJAK" in line:
                    for offset in [1, 2]:
                        if i + offset < len(lines):
                            parts = lines[i+offset].split()
                            for p in parts:
                                if any(char.isdigit() for char in p) and len(p) > 5:
                                    nomor_bupot = p.strip()
                                    break
                        if nomor_bupot: break

                # 3. REVISI: Ambil Nomor Dokumen (B.9) - Mengambil semua karakter
                if "Nomor Dokumen" in line:
                    # Mengambil teks setelah tanda titik dua (:) 
                    if ":" in line:
                        nomor_dokumen = line.split(":", 1)[1].strip()
                    else:
                        # Fallback jika tidak ada titik dua
                        nomor_dokumen = line.replace("Nomor Dokumen", "").strip()
            
            return nama, nomor_bupot, nomor_dokumen
    except Exception:
        return None, None, None

# --- UI STREAMLIT ---
st.set_page_config(page_title="Bupot Renamer Pro", page_icon="📑", layout="wide")

st.title("📑 Bupot Auto-Rename & Data Export")
st.write("Unggah PDF Bukti Potong, lihat pratinjau data, lalu unduh file PDF atau rekap Excel-nya.")

# Widget Unggah File
uploaded_files = st.file_uploader(
    "Seret dan lepas file PDF di sini", 
    type="pdf", 
    accept_multiple_files=True
)

if uploaded_files:
    data_list = []
    processed_files = []
    
    my_bar = st.progress(0, text="Sedang membaca file...")

    for index, file in enumerate(uploaded_files):
        nama, bupot, dok = extract_info(file)
        
        if nama and bupot and dok:
            # Membersihkan karakter ilegal untuk nama file (terutama jika No Dokumen ada "/")
            new_filename = f"{nama} {bupot} {dok}.pdf"
            new_filename = re.sub(r'[\\/*?:"<>|]', "_", new_filename) # Ubah karakter terlarang jadi underscore
            status = "✅ Berhasil"
        else:
            new_filename = f"GAGAL_BACA_{file.name}"
            status = "❌ Gagal Ekstrak"

        # Simpan untuk Tabel & Excel
        data_list.append({
            "Nama File Asli": file.name,
            "Nama Baru": new_filename,
            "Nama Wajib Pajak (A.2)": nama,
            "No Bupot": bupot,
            "No Dokumen (B.9)": dok,
            "Status": status
        })

        processed_files.append({
            "content": file.getvalue(),
            "filename": new_filename
        })
        
        my_bar.progress((index + 1) / len(uploaded_files), text=f"Memproses {index+1}/{len(uploaded_files)}")

    # --- TAMPILKAN TABEL PREVIEW ---
    st.subheader("📊 Pratinjau Data")
    df = pd.DataFrame(data_list)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # --- AREA DOWNLOAD ---
    st.divider()
    st.subheader("📥 Unduh Hasil")
    col1, col2, col3 = st.columns(3)

    # 1. Download ZIP (PDF hasil rename)
    with col1:
        if processed_files:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for f in processed_files:
                    zf.writestr(f["filename"], f["content"])
            
            st.download_button(
                label="📁 Download Semua PDF (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="bupot_renamed.zip",
                mime="application/zip",
                use_container_width=True
            )

    # 2. Download Excel (Rekap Data)
    with col2:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Data_Bupot')
        
        st.download_button(
            label="📊 Download Rekap (Excel)",
            data=excel_buffer.getvalue(),
            file_name="rekap_bupot.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # 3. Tombol Reset
    with col3:
        if st.button("🗑️ Bersihkan Semua", use_container_width=True):
            st.rerun()

# --- SIDEBAR INFO ---
with st.sidebar:
    st.header("Info Program")
    st.info("""
    - **Rename Otomatis**: Mengambil Nama, No Bupot, dan No Dokumen.
    - **Karakter Aman**: Simbol seperti `/` pada nomor dokumen akan otomatis diubah menjadi `_` agar file bisa disimpan.
    """)
