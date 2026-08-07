import streamlit as st
import requests


st.title("Apps'o pavadinimas")

st.write("Įkelkite garso failą transkribavimui.")


def garso_i_teksta(audio_file):

    url = "https://api.deepgram.com/v1/listen"

    params = {
        "model": "nova-3-general",
        "detect_language": "true",
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

    tekstas = (
        rezultatas["results"]
        ["channels"][0]
        ["alternatives"][0]
        ["transcript"]
    )

    return tekstas


ikeltas_garso_failas = st.file_uploader(
    "Įkelkite garso failą",
    type=["mp3", "wav", "m4a", "ogg", "flac"]
)


if ikeltas_garso_failas is not None:

    st.audio(ikeltas_garso_failas)

    if st.button("Transkribuoti"):

        with st.spinner("Garso failas transkribuojamas..."):

            try:

                tekstas = garso_i_teksta(
                    ikeltas_garso_failas
                )

                st.session_state["tekstas"] = tekstas

                st.success("Transkribavimas baigtas!")

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