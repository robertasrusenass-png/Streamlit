import streamlit as st
import requests


st.title("Apps'o pavadinimas")

st.write("Įkelkite garso failą transkribavimui.")

kalbos = {
    "Automatiškai (LT / RU)": "auto",
    "Lietuvių": "lt",
    "Rusų": "ru"
}

pasirinkta_kalba = st.selectbox(
    "Pasirinkite garso kalbą",
    list(kalbos.keys())
)



def garso_i_teksta(audio_file, kalba):

    url = "https://api.deepgram.com/v1/listen"

    if kalba == "auto":
        params = [
            ("model", "nova-3-general"),
            ("detect_language", "lt"),
            ("detect_language", "ru"),
            ("smart_format", "true")
        ]
    else:
        params = {
            "model": "nova-3-general",
            "language": kalba,
            "smart_format": "true"
        }

    headers = {
        "Authorization": f"Token {st.secrets['DEEPGRAM_API_KEY']}",
        "Content-Type": audio_file.type
    }

    response = requests.post(
        url,
        params=params,
        headers=headers,
        data=audio_file.getvalue(),
        timeout=300
    )

    if response.status_code != 200:
        raise Exception(
        f"Deepgram klaida {response.status_code}: {response.text}"
        )

    rezultatas = response.json()

    channel = rezultatas["results"]["channels"][0]

    tekstas = channel["alternatives"][0]["transcript"]

    aptikta_kalba = channel.get(
            "detected_language",
            "nežinoma"
        )

    kalbos_patimumas = channel.get(
        "language_confidence",
        0
    )

    trukme = rezultatas.get(
        "metadata",
        {}
    ).get(
        "duration",
        0
    )

    return tekstas, aptikta_kalba, kalbos_patimumas, trukme


ikeltas_garso_failas = st.file_uploader(
    "Įkelkite garso failą",
    type=["mp3", "wav", "m4a", "ogg", "flac"]
)


if ikeltas_garso_failas is not None:

    st.audio(ikeltas_garso_failas)

    if st.button("Transkribuoti"):

        with st.spinner("Garso failas transkribuojamas..."):

            try:

                kalbos_kodas = kalbos[pasirinkta_kalba]
                
                tekstas, kalba, patikimumas, trukme = garso_i_teksta(
                    ikeltas_garso_failas,
                    kalbos_kodas
                )

                st.write(f"Aptikta kalba: **{kalba}**")
                st.write(f"Kalbos aptikimo patikimumas: **{patikimumas:.2%}**")
                st.write(f"Garso trukmė: **{trukme:.1f} s**")
                if tekstas.strip():

                    st.session_state["tekstas"] = tekstas
                    st.success("Transkribavimas baigtas!")

                else:

                    st.warning(
                        "Deepgram apdorojo failą, "
                        "bet jame neatpažino kalbos."
                    )

            except Exception as e:

                st.error(f"Įvyko klaida: {e}")


if "tekstas" in st.session_state:

    st.text_area(
        "Transkribuotas tekstas",
        value=st.session_state["tekstas"],
        height=400
    )

    st.download_button(
        "Atsisiųsti tekstą",
        data=st.session_state["tekstas"],
        file_name="transkriptas.txt",
        mime="text/plain"
    )